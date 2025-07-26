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
