from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, FastAPI, Response
from httpx import AsyncClient
import pytest

from src.fastapi_easy_versioning import (
    VersioningMiddleware,
    VersioningSupport,
    versioning,
)

pytestmark = [pytest.mark.anyio]


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
        version: Annotated[VersioningSupport, Depends(versioning())],
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
    so the endpoint is not inherited anywhere.
    """
    fake = FastAPI(api_version=True)
    app.mount("/fake", fake)

    def endpoint(_: Annotated[VersioningSupport, Depends(versioning())]) -> None: ...

    fake.router.add_api_route("/test", endpoint)

    response = await client.get("/v2/test")

    assert response.status_code == HTTPStatus.NOT_FOUND


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
