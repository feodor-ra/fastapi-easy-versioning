from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient
import pytest

from src.fastapi_easy_versioning import VersioningMiddleware

WebSocketRequest = Callable[..., Awaitable[tuple[bool, list[str]]]]


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def app() -> FastAPI:
    return FastAPI()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        base_url="http://1.2.3.4:123/",
        transport=ASGITransport(app, client=("1.2.3.4", 123)),
    ) as client:
        yield client


@pytest.fixture
def middleware_setup(app: FastAPI) -> None:
    app.add_middleware(VersioningMiddleware)


@pytest.fixture
def websocket_request(app: FastAPI) -> WebSocketRequest:
    """Minimal raw-ASGI WebSocket client against the root app.

    Neither httpx2 nor httpx supports WebSocket natively, and starlette's
    TestClient requires the httpx package, so the handshake is driven by hand.

    Returns:
        Callable performing one round trip; it returns a tuple of the accepted
        flag and the received text messages.

    """

    async def request(
        path: str, *, send_text: str | None = None
    ) -> tuple[bool, list[str]]:
        outgoing: list[dict[str, Any]] = [{"type": "websocket.connect"}]
        if send_text is not None:
            outgoing.append({"type": "websocket.receive", "text": send_text})
        outgoing.append({"type": "websocket.disconnect", "code": 1000})
        incoming: list[dict[str, Any]] = []
        messages = iter(outgoing)

        # ASGI receive/send callables must be async regardless of their bodies.
        async def receive() -> dict[str, Any]:  # noqa: RUF029
            return next(messages)

        async def send(message: dict[str, Any]) -> None:  # noqa: RUF029
            incoming.append(message)

        scope: dict[str, Any] = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "scheme": "ws",
            "http_version": "1.1",
            "path": path,
            "raw_path": path.encode(),
            "root_path": "",
            "query_string": b"",
            "headers": [],
            "client": ("1.2.3.4", 123),
            "server": ("1.2.3.4", 123),
            "subprotocols": [],
        }
        await app(scope, receive, send)
        accepted = any(item["type"] == "websocket.accept" for item in incoming)
        texts = [
            item["text"]
            for item in incoming
            if item["type"] == "websocket.send" and "text" in item
        ]
        return accepted, texts

    return request


@pytest.fixture
def v1(app: FastAPI) -> FastAPI:
    v1 = FastAPI(api_version=1)
    app.mount("/v1", v1)
    return v1


@pytest.fixture
def v2(app: FastAPI) -> FastAPI:
    v2 = FastAPI(api_version=2)
    app.mount("/v2", v2)
    return v2
