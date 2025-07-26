from typing import Callable

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from src.fastapi_easy_versioning import VersioningMiddleware


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def app() -> FastAPI:
    return FastAPI()


@pytest.fixture
def client(app: FastAPI) -> AsyncClient:
    return AsyncClient(
        base_url="http://1.2.3.4:123/",
        transport=ASGITransport(app, client=("1.2.3.4", 123)),
    )


@pytest.fixture
def setup_middleware() -> Callable[[FastAPI], None]:
    def setup(app: FastAPI) -> None:
        app.add_middleware(VersioningMiddleware)

    return setup


@pytest.fixture
def middleware_setup(setup_middleware: Callable[[FastAPI], None], app: FastAPI) -> None:
    setup_middleware(app)
