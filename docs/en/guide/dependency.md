---
title: Dependency
---

# Versioning Dependency

The `versioning()` factory is how an endpoint is marked as versioned. It returns a `VersioningSupport` instance suitable for `Depends()`.

!!! info "Marking is mandatory"

    An endpoint without this dependency does not participate in versioning: it is never inherited into newer versions and stays only where it is declared. This is a deliberate opt-in, not a default.

## The `until` semantics { #until }

`versioning(*, until: int | None = None)` controls the range of versions an endpoint is available in:

| Value | Behaviour |
| --- | --- |
| `until=None` (default) | The endpoint is available from its own version onwards, in every later one |
| `until=N` | The endpoint is available from its own version through version `N`, inclusive |

Extra rules:

- If a route carries several `versioning` dependencies (say, one on the router and one on the endpoint), the **smallest** declared `until` wins.
- An `until` below the version that declares the endpoint is a contradiction: the library emits a `UserWarning`, the endpoint stays available in its own version but is inherited nowhere.

!!! warning "`versioning()` does not mean \"this version only\""

    Called without arguments it means "available through the latest version", including versions mounted later. To limit an endpoint to a single version, pass an `until` equal to that version's number.

## Ways to attach it

The dependency is accepted everywhere FastAPI accepts dependencies:

```python
from fastapi import APIRouter, Depends, FastAPI
from fastapi_easy_versioning import versioning

v1_app = FastAPI(api_version=1)


# On an endpoint — through the decorator
@v1_app.get("/endpoint", dependencies=[Depends(versioning())])
def endpoint() -> None: ...


# Through add_api_route
v1_app.add_api_route("/added", endpoint, dependencies=[Depends(versioning(until=2))])

# On a whole router at once — every endpoint of it is versioned
router = APIRouter(dependencies=[Depends(versioning())])


@router.get("/router-endpoint")
def router_endpoint() -> None: ...


v1_app.include_router(router)
```

## Reading the metadata inside an endpoint

The dependency can be injected into an endpoint — then it returns a `VersionInfo` named tuple with the route's resolved versioning configuration:

- `origin` — the version that declared the endpoint;
- `until` — the last version the endpoint is available in. If no `until` was declared explicitly, this is the latest existing API version.

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi_easy_versioning import VersionInfo, versioning

v1_app = FastAPI(api_version=1)


@v1_app.get("/endpoint")
def endpoint(version: Annotated[VersionInfo, Depends(versioning())]) -> str:
    return f"Available from version {version.origin} through version {version.until}"
```

Injection works in WebSocket endpoints too:

```python
from typing import Annotated

from fastapi import Depends, FastAPI, WebSocket
from fastapi_easy_versioning import VersionInfo, versioning

v1_app = FastAPI(api_version=1)


@v1_app.websocket("/ws")
async def ws_endpoint(
    websocket: WebSocket,
    version: Annotated[VersionInfo, Depends(versioning())],
) -> None:
    await websocket.accept()
    await websocket.send_text(f"Available from version {version.origin}")
    await websocket.close()
```

## Diagnostics { #diagnostics }

If versioning has not been initialized, injecting `VersionInfo` fails with a `RuntimeError` listing the possible causes:

- `VersioningMiddleware` is not added to the application that mounts the versions;
- the sub-application was not created with `FastAPI(api_version=<int>)`;
- the route was registered after the first request and [`rebuild_versioning`](middleware.md#runtime) was never called.

!!! tip "Full reference"

    Signatures and detailed descriptions live in the [API reference](../reference/dependency.md).
