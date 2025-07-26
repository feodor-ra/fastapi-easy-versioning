from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, FastAPI
from httpx import AsyncClient
import pytest

from src.fastapi_easy_versioning import (
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


async def test_export_versioning_without_use_middleware(
    client: AsyncClient, app: FastAPI, v1: FastAPI
) -> None:
    """Export versioning data without setup middleware.

    If try export VersioningSupport
    without setup middleware this raises RuntimeError.
    """

    def endpoint(_: Annotated[VersioningSupport, Depends(versioning())]) -> None: ...

    v1.router.add_api_route("/test", endpoint, name="test")

    with pytest.raises(RuntimeError, match="VersioningMiddleware not used"):
        await client.get(app.url_path_for("test"))


@pytest.mark.parametrize("from_version", [1, 2])
@pytest.mark.usefixtures("middleware_setup")
async def test_export_until_with_use_middleware(
    from_version: int,
    client: AsyncClient,
    v1: FastAPI,
    v2: FastAPI,
) -> None:
    """Export until version with setup middleware.

    If try export unset until version
    with setup middleware returns latest available version.
    """

    def endpoint(version: Annotated[VersioningSupport, Depends(versioning())]) -> None:
        assert version.until == v2.extra["api_version"]

    v1.router.add_api_route("/test", endpoint)

    await client.get(f"/v{from_version}/test")


@pytest.mark.parametrize("from_version", [1, 2])
@pytest.mark.usefixtures("v2", "middleware_setup")
async def test_export_origin_with_use_middleware(
    from_version: int,
    client: AsyncClient,
    v1: FastAPI,
) -> None:
    """Export origin version with setup middleware.

    If try export origin version
    with setup middleware returns api_version of app there was included.
    """

    def endpoint(version: Annotated[VersioningSupport, Depends(versioning())]) -> None:
        assert version.origin == v1.extra["api_version"]

    v1.router.add_api_route("/test", endpoint)

    await client.get(f"/v{from_version}/test")


@pytest.mark.usefixtures("v2", "middleware_setup")
async def test_require_endpoint_without_dependency(
    client: AsyncClient,
    v1: FastAPI,
) -> None:
    """Try require endpoint without dependency from next version.

    This response 404 code.
    """
    v1.router.add_api_route("/test", lambda: None, name="test")
    response = await client.get("/v2/test")
    assert response.status_code == HTTPStatus.NOT_FOUND
