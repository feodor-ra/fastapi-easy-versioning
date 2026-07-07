from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, FastAPI
from httpx2 import AsyncClient
import pytest

from src.fastapi_easy_versioning import VersionInfo, versioning

pytestmark = [pytest.mark.anyio]


async def test_export_versioning_without_use_middleware(
    client: AsyncClient, app: FastAPI, v1: FastAPI
) -> None:
    """Export versioning data without setup middleware.

    If try export VersionInfo
    without setup middleware this raises RuntimeError.
    """

    def endpoint(_: Annotated[VersionInfo, Depends(versioning())]) -> None: ...

    v1.router.add_api_route("/test", endpoint, name="test")

    with pytest.raises(RuntimeError, match="Versioning is not initialized"):
        await client.get(app.url_path_for("test"))


@pytest.mark.parametrize("from_version", [1, 2])
@pytest.mark.usefixtures("middleware_setup")
async def test_export_versioning_metadata(
    from_version: int,
    client: AsyncClient,
    v1: FastAPI,
    v2: FastAPI,
) -> None:
    """Export versioning metadata with setup middleware.

    Both the declaring and the inheriting version respond with the
    declaring version as origin and the latest version as until.
    """

    def endpoint(
        version: Annotated[VersionInfo, Depends(versioning())],
    ) -> dict[str, int]:
        return {"origin": version.origin, "until": version.until}

    v1.router.add_api_route("/test", endpoint)

    response = await client.get(f"/v{from_version}/test")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "origin": v1.extra["api_version"],
        "until": v2.extra["api_version"],
    }


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
