from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, WebSocket
from fastapi.routing import APIWebSocketRoute
from httpx2 import AsyncClient
import pytest

from src.fastapi_easy_versioning import VersionInfo, versioning
from tests.conftest import WebSocketRequest

pytestmark = [pytest.mark.anyio]


@pytest.mark.usefixtures("v2", "middleware_setup")
async def test_websocket_endpoint_inherited(
    websocket_request: WebSocketRequest,
    v1: FastAPI,
) -> None:
    """Require a versioned websocket endpoint from the next version.

    The endpoint is inherited and exports its versioning metadata.
    """

    async def endpoint(
        websocket: WebSocket,
        version: Annotated[VersionInfo, Depends(versioning())],
    ) -> None:
        await websocket.accept()
        await websocket.send_text(f"origin={version.origin} until={version.until}")
        await websocket.close()

    v1.router.add_api_websocket_route("/ws", endpoint)

    declared = await websocket_request("/v1/ws")
    inherited = await websocket_request("/v2/ws")

    assert declared == (True, ["origin=1 until=2"])
    assert inherited == (True, ["origin=1 until=2"])


@pytest.mark.usefixtures("v2", "middleware_setup")
async def test_websocket_until_limits_inheritance(
    websocket_request: WebSocketRequest,
    v1: FastAPI,
) -> None:
    """Try require websocket endpoint from next version after until version.

    The connection to the newer version is not accepted.
    """

    async def endpoint(
        websocket: WebSocket,
        _: Annotated[VersionInfo, Depends(versioning(until=1))],
    ) -> None:
        await websocket.accept()
        await websocket.close()

    v1.router.add_api_websocket_route("/ws", endpoint)

    declared = await websocket_request("/v1/ws")
    limited = await websocket_request("/v2/ws")

    assert declared[0] is True
    assert limited[0] is False


@pytest.mark.usefixtures("middleware_setup")
async def test_redefined_websocket_shadows_inherited(
    websocket_request: WebSocketRequest,
    v1: FastAPI,
    v2: FastAPI,
) -> None:
    """Redefine a versioned websocket endpoint in a newer version.

    The newer version's own endpoint wins and the old one is not inherited.
    """

    async def v1_endpoint(
        websocket: WebSocket,
        _: Annotated[VersionInfo, Depends(versioning())],
    ) -> None:
        await websocket.accept()
        await websocket.send_text("v1")
        await websocket.close()

    async def v2_endpoint(
        websocket: WebSocket,
        _: Annotated[VersionInfo, Depends(versioning())],
    ) -> None:
        await websocket.accept()
        await websocket.send_text("v2")
        await websocket.close()

    v1.router.add_api_websocket_route("/ws", v1_endpoint)
    v2.router.add_api_websocket_route("/ws", v2_endpoint)

    declared = await websocket_request("/v1/ws")
    redefined = await websocket_request("/v2/ws")

    assert declared == (True, ["v1"])
    assert redefined == (True, ["v2"])
    v2_ws_routes = [
        route
        for route in v2.router.routes
        if isinstance(route, APIWebSocketRoute) and route.path == "/ws"
    ]
    assert len(v2_ws_routes) == 1


@pytest.mark.usefixtures("v2", "middleware_setup")
async def test_included_router_websocket_with_prefix(
    websocket_request: WebSocketRequest,
    v1: FastAPI,
) -> None:
    """Include a router with prefixes containing a versioned websocket.

    The effective path (router prefix + include prefix) is inherited.
    """
    router = APIRouter(prefix="/sub")

    async def endpoint(
        websocket: WebSocket,
        version: Annotated[VersionInfo, Depends(versioning())],
    ) -> None:
        await websocket.accept()
        await websocket.send_text(f"v{version.origin}")
        await websocket.close()

    router.add_api_websocket_route("/ws", endpoint)
    v1.include_router(router, prefix="/nested")

    declared = await websocket_request("/v1/nested/sub/ws")
    inherited = await websocket_request("/v2/nested/sub/ws")

    assert declared == (True, ["v1"])
    assert inherited == (True, ["v1"])


@pytest.mark.usefixtures("middleware_setup")
async def test_http_and_websocket_share_path(
    client: AsyncClient,
    websocket_request: WebSocketRequest,
    v1: FastAPI,
    v2: FastAPI,
) -> None:
    """Version an HTTP endpoint and a websocket sharing the same path.

    Shadowing is kind-aware: the newer version's own HTTP endpoint shadows
    only the HTTP one, the websocket is still inherited.
    """

    async def ws_endpoint(
        websocket: WebSocket,
        _: Annotated[VersionInfo, Depends(versioning())],
    ) -> None:
        await websocket.accept()
        await websocket.send_text("ws-v1")
        await websocket.close()

    v1.router.add_api_route(
        "/both", lambda: "http-v1", dependencies=[Depends(versioning())]
    )
    v1.router.add_api_websocket_route("/both", ws_endpoint)
    v2.router.add_api_route(
        "/both", lambda: "http-v2", dependencies=[Depends(versioning())]
    )

    http_response = await client.get("/v2/both")
    ws_response = await websocket_request("/v2/both")

    assert http_response.json() == "http-v2"
    assert ws_response == (True, ["ws-v1"])
