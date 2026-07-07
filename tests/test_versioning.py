from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Response
from httpx import AsyncClient
import pytest

from src.fastapi_easy_versioning import (
    VersionInfo,
    VersioningMiddleware,
    VersioningSupport,
    rebuild_versioning,
    versioning,
)

pytestmark = [pytest.mark.anyio]


@pytest.mark.usefixtures("v2")
async def test_require_versioning_endpoint_without_use_middleware(
    client: AsyncClient,
    v1: FastAPI,
) -> None:
    """Try require versioning endpoint from next version without setup middleware.

    This response 404 code.
    """

    def endpoint(_: Annotated[VersioningSupport, Depends(versioning())]) -> None: ...

    v1.router.add_api_route("/test", endpoint)

    response = await client.get("/v2/test")

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.usefixtures("v2", "middleware_setup")
async def test_require_versioning_endpoint_with_use_middleware(
    client: AsyncClient,
    v1: FastAPI,
) -> None:
    """Try require versioning endpoint from next version with setup middleware.

    This response 200 code.
    """

    def endpoint(_: Annotated[VersioningSupport, Depends(versioning())]) -> None: ...

    v1.router.add_api_route("/test", endpoint)

    response = await client.get("/v2/test")

    assert response.status_code == HTTPStatus.OK


@pytest.mark.usefixtures("v2", "middleware_setup")
async def test_require_versioning_endpoint_after_until(
    client: AsyncClient,
    v1: FastAPI,
) -> None:
    """Try require versioning endpoint from next version after until version.

    This response 404 code.
    """

    def endpoint(
        _: Annotated[VersioningSupport, Depends(versioning(until=1))],
    ) -> None: ...

    v1.router.add_api_route("/test", endpoint)

    response = await client.get("/v2/test")

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.usefixtures("middleware_setup")
async def test_require_endpoint_without_any_versioned_mounts(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """Try require endpoint when middleware is set up but no versioned app is mounted.

    This response 200 code instead of crashing every request.
    """
    app.mount("/sub", FastAPI())
    app.router.add_api_route("/plain", lambda: None)

    response = await client.get("/plain")

    assert response.status_code == HTTPStatus.OK


@pytest.mark.usefixtures("middleware_setup")
async def test_require_versioning_endpoint_from_app_without_extra(
    client: AsyncClient,
    app: FastAPI,
    v1: FastAPI,
) -> None:
    """Try require versioning endpoint from app version without extra api_version.

    This response 404 code.
    """

    def endpoint(
        _: Annotated[VersioningSupport, Depends(versioning())],
    ) -> None: ...

    app.mount("/v3", FastAPI())
    app.mount("/v4", FastAPI(api_version=4))
    v1.router.add_api_route("/test", endpoint)

    response = await client.get("/v3/test")

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.usefixtures("middleware_setup")
async def test_version_zero_survives_rebuild(
    client: AsyncClient,
    app: FastAPI,
    v1: FastAPI,
) -> None:
    """Require versioning endpoint declared in version 0 twice with rebuild between.

    Version 0 is a valid api_version and origin must stay 0 after a rebuild.
    """
    v0 = FastAPI(api_version=0)
    app.mount("/v0", v0)

    def endpoint(
        version: Annotated[VersionInfo, Depends(versioning())],
    ) -> dict[str, int]:
        return {"origin": version.origin, "until": version.until}

    v0.router.add_api_route("/test", endpoint)

    first = await client.get("/v0/test")
    v1.router.add_api_route("/new", lambda: None, dependencies=[Depends(versioning())])
    second = await client.get("/v0/test")

    assert first.status_code == HTTPStatus.OK
    assert first.json() == {"origin": 0, "until": 1}
    assert second.status_code == HTTPStatus.OK
    assert second.json() == {"origin": 0, "until": 1}


@pytest.mark.usefixtures("v2", "middleware_setup")
async def test_bool_api_version_is_not_a_version(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """Try require versioning endpoint from an app with bool api_version.

    bool is not a version number (True must not be treated as version 1),
    so the endpoint is not inherited anywhere and a warning is emitted.
    """
    fake = FastAPI(api_version=True)
    app.mount("/fake", fake)

    def endpoint(_: Annotated[VersioningSupport, Depends(versioning())]) -> None: ...

    fake.router.add_api_route("/test", endpoint)

    with pytest.warns(UserWarning, match="api_version=True"):
        response = await client.get("/v2/test")

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.usefixtures("v2", "middleware_setup")
async def test_router_level_versioning_does_not_leak_until(
    client: AsyncClient,
    v1: FastAPI,
) -> None:
    """Require sibling endpoints of a router with router-level versioning().

    A per-route until on one endpoint must not leak into siblings through
    the shared router-level dependency instance.
    """
    router = APIRouter(dependencies=[Depends(versioning())])
    router.add_api_route(
        "/limited", lambda: None, dependencies=[Depends(versioning(until=1))]
    )
    router.add_api_route("/forever", lambda: None)
    v1.include_router(router)

    limited = await client.get("/v2/limited")
    forever = await client.get("/v2/forever")

    assert limited.status_code == HTTPStatus.NOT_FOUND
    assert forever.status_code == HTTPStatus.OK


@pytest.mark.usefixtures("middleware_setup")
async def test_shared_router_reports_declaring_version(
    client: AsyncClient,
    v1: FastAPI,
    v2: FastAPI,
) -> None:
    """Include the same router into two versions and export origin from both.

    Each version's own copy of the route must report the version it was
    included into, not the state frozen by the first processed copy.
    """
    router = APIRouter()

    def endpoint(
        version: Annotated[VersionInfo, Depends(versioning())],
    ) -> dict[str, int]:
        return {"origin": version.origin}

    router.add_api_route("/test", endpoint)
    v1.include_router(router)
    v2.include_router(router)

    first = await client.get("/v1/test")
    second = await client.get("/v2/test")

    assert first.json() == {"origin": 1}
    assert second.json() == {"origin": 2}


@pytest.mark.usefixtures("middleware_setup")
async def test_redefined_endpoint_shadows_inherited(
    client: AsyncClient,
    v1: FastAPI,
    v2: FastAPI,
) -> None:
    """Redefine a versioned endpoint in a newer version.

    The newer version's own endpoint must win both at runtime and in the
    OpenAPI schema; the older route is not inherited into that version.
    """
    v1.router.add_api_route(
        "/test", lambda: "v1", dependencies=[Depends(versioning())], name="from_v1"
    )
    v2.router.add_api_route(
        "/test", lambda: "v2", dependencies=[Depends(versioning())], name="from_v2"
    )

    response = await client.get("/v2/test")

    assert response.json() == "v2"
    assert v2.openapi_schema is not None
    assert "from_v2" in v2.openapi_schema["paths"]["/test"]["get"]["operationId"]
    test_routes = [r for r in v2.router.routes if getattr(r, "path", None) == "/test"]
    assert len(test_routes) == 1


@pytest.mark.usefixtures("middleware_setup")
async def test_dependency_overrides_resolved_by_serving_version(
    client: AsyncClient,
    v1: FastAPI,
    v2: FastAPI,
) -> None:
    """Override a dependency of an inherited route on the serving version's app.

    dependency_overrides must be taken from the app that serves the request,
    not only from the app that declared the route.
    """

    def get_flag() -> str:
        return "real"

    def endpoint(
        flag: Annotated[str, Depends(get_flag)],
        _: Annotated[VersioningSupport, Depends(versioning())],
    ) -> dict[str, str]:
        return {"flag": flag}

    v1.router.add_api_route("/test", endpoint)
    v2.dependency_overrides[get_flag] = lambda: "overridden"

    v1_response = await client.get("/v1/test")
    v2_response = await client.get("/v2/test")

    assert v1_response.json() == {"flag": "real"}
    assert v2_response.json() == {"flag": "overridden"}


@pytest.mark.usefixtures("middleware_setup")
async def test_runtime_routes_require_explicit_rebuild(
    client: AsyncClient,
    app: FastAPI,
    v1: FastAPI,
    v2: FastAPI,
) -> None:
    """Require versioning endpoint added at runtime after the first request.

    Routes are built once on the first ASGI event: a runtime-added endpoint
    is not inherited until `rebuild_versioning` is called explicitly, and the
    explicit rebuild also refreshes the cached OpenAPI schema.
    """
    await client.get("/v1/warmup")
    v1.router.add_api_route("/new", lambda: None, dependencies=[Depends(versioning())])

    before_rebuild = await client.get("/v2/new")
    rebuild_versioning(app)
    after_rebuild = await client.get("/v2/new")

    assert before_rebuild.status_code == HTTPStatus.NOT_FOUND
    assert after_rebuild.status_code == HTTPStatus.OK
    assert v2.openapi_schema is not None
    assert "/new" in v2.openapi_schema["paths"]


async def test_multiple_independent_versioned_apps(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """Version two mounted apps independently with their own middleware.

    Each middleware instance versions only the sub-apps mounted directly
    under its own app, as in examples/multiple_versioning.py.
    """
    public = FastAPI()
    public.add_middleware(VersioningMiddleware)
    private = FastAPI()
    private.add_middleware(VersioningMiddleware)
    app.mount("/public", public)
    app.mount("/private", private)
    public_v1 = FastAPI(api_version=1)
    private_v1 = FastAPI(api_version=1)
    public.mount("/v1", public_v1)
    public.mount("/v2", FastAPI(api_version=2))
    private.mount("/v1", private_v1)
    private.mount("/v2", FastAPI(api_version=2))

    public_v1.router.add_api_route(
        "/endpoint", lambda: None, dependencies=[Depends(versioning())]
    )
    private_v1.router.add_api_route(
        "/endpoint", lambda: None, dependencies=[Depends(versioning(until=1))]
    )

    inherited = await client.get("/public/v2/endpoint")
    limited = await client.get("/private/v2/endpoint")
    declared = await client.get("/private/v1/endpoint")

    assert inherited.status_code == HTTPStatus.OK
    assert limited.status_code == HTTPStatus.NOT_FOUND
    assert declared.status_code == HTTPStatus.OK


def test_invalid_api_version_warns(app: FastAPI) -> None:
    """Mount an app whose api_version is not an int and rebuild.

    The mount is ignored, but a warning must point at it instead of silence.
    """
    app.mount("/broken", FastAPI(api_version="1"))

    with pytest.warns(UserWarning, match="api_version='1'"):
        rebuild_versioning(app)


@pytest.mark.usefixtures("v1")
def test_until_below_declaring_version_warns(app: FastAPI, v2: FastAPI) -> None:
    """Declare an endpoint in version 2 versioned until version 1 and rebuild.

    The contradictory until must produce a warning.
    """
    v2.router.add_api_route(
        "/test", lambda: None, dependencies=[Depends(versioning(until=1))]
    )

    with pytest.warns(UserWarning, match="until=1"):
        rebuild_versioning(app)


async def test_require_versioning_endpoint_without_openapi_rebuild(
    client: AsyncClient, app: FastAPI, v1: FastAPI, v2: FastAPI
) -> None:
    """Try require versioning endpoint from previous version with disabled OpenAPI rebuild.

    This response 204 code.
    """  # noqa: E501
    expected_status = HTTPStatus.NO_CONTENT
    app.add_middleware(VersioningMiddleware, rebuild_openapi=False)
    v1.add_api_route(
        "/test",
        lambda: Response(status_code=expected_status),
        dependencies=[Depends(versioning())],
    )
    openapi_before = v2.openapi_schema

    response = await client.get("/v2/test")
    openapi_after = v2.openapi_schema

    assert response.status_code == expected_status
    assert openapi_before == openapi_after
