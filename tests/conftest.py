from collections.abc import AsyncIterator

from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient
import pytest

from src.fastapi_easy_versioning import VersioningMiddleware


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
def v1(app: FastAPI) -> FastAPI:
    v1 = FastAPI(api_version=1)
    app.mount("/v1", v1)
    return v1


@pytest.fixture
def v2(app: FastAPI) -> FastAPI:
    v2 = FastAPI(api_version=2)
    app.mount("/v2", v2)
    return v2
