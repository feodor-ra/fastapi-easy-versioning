from typing import Annotated

from fastapi import Depends, FastAPI, middleware
from fastapi_easy_versioning import (
    VersioningMiddleware,
    VersioningSupport,
    versioning,
)

app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware)])
app_v1 = FastAPI(api_version=1)
app_v2 = FastAPI(api_version=2)
app_v3 = FastAPI(api_version=3)

app.mount("/v1", app_v1)
app.mount("/v2", app_v2)
app.mount("/v3", app_v3)


@app_v1.get("/endpoint", dependencies=[Depends(versioning(until=2))])
def endpoint() -> str:
    return "I'm v1 endpoint"


@app_v1.get("/another-endpoint")
def another_endpoint(
    version: Annotated[VersioningSupport, Depends(versioning())],
) -> str:
    return f"I'm v{version.origin} another endpoint"


@app_v2.get("/new-another-endpoint", dependencies=[Depends(versioning())])
def new_another_endpoint() -> str:
    return "I'm v2 new another endpoint"


@app_v3.get("/another-endpoint", dependencies=[Depends(versioning())])
def overload_another_endpoint() -> str:
    return "I'm v3 overloaded another endpoint"


# To run this example use:
# uvx --python=3.13 --from="fastapi[standard]" --with="fastapi-easy-versioning" fastapi dev examples/simple_versioning.py
