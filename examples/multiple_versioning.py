from fastapi import Depends, FastAPI, middleware
from fastapi_easy_versioning import (
    VersioningMiddleware,
    versioning,
)

app = FastAPI()

public_app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware)])
public_v1 = FastAPI(api_version=1)
public_v2 = FastAPI(api_version=2)

private_app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware)])
private_v1 = FastAPI(api_version=1)
private_v2 = FastAPI(api_version=2)

app.mount("/api/public", public_app)
public_app.mount("/v1", public_v1)
public_app.mount("/v2", public_v2)

app.mount("/api/private", private_app)
private_app.mount("/v1", private_v1)
private_app.mount("/v2", private_v2)


@private_v1.get("/endpoint", dependencies=[Depends(versioning(until=1))])
def private_endpoint() -> str:
    return "I'm v1 private endpoint"


@private_v1.get("/another-endpoint", dependencies=[Depends(versioning())])
def private_another_endpoint() -> str:
    return "I'm v1 private another endpoint"


@private_v2.get("/endpoint", dependencies=[Depends(versioning())])
def private_endpoint_v2() -> str:
    return "I'm v2 private endpoint"


@public_v1.get("/endpoint", dependencies=[Depends(versioning(until=1))])
def public_endpoint() -> str:
    return "I'm v1 public endpoint"


@public_v1.get("/another-endpoint", dependencies=[Depends(versioning())])
def public_another_endpoint() -> str:
    return "I'm v1 public another endpoint"


@public_v2.get("/endpoint", dependencies=[Depends(versioning())])
def public_endpoint_v2() -> str:
    return "I'm v2 public endpoint"


# To run this example use:
# uvx --python=3.13 --from="fastapi[standard]" --with="fastapi-easy-versioning" fastapi dev examples/multiple_versioning.py
