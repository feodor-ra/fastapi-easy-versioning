# Versioning Dependency

The `versioning()` factory is how an endpoint is marked as versioned. It returns a `VersioningSupport` instance suitable for `Depends()`. An endpoint without this dependency does not participate in versioning and stays only in the version where it is declared.

## `until` Semantics

`versioning(*, until: int | None = None)` controls the range of versions the endpoint is available in:

| Value | Behavior |
| --- | --- |
| `until=None` (default) | The endpoint is available from its own version and in all subsequent ones |
| `until=N` | The endpoint is available from its own version up to and including version `N` |

Additional rules:

- If a route has several `versioning` dependencies (for example, one on the router and one on the endpoint), the **minimum** of the declared `until` values wins.
- An `until` lower than the version the endpoint is declared in is a contradiction: the library emits a `UserWarning`, and the endpoint stays available in its own version but is inherited nowhere.

## Where to Attach It

The dependency is accepted everywhere FastAPI accepts dependencies:

```python
from fastapi import APIRouter, Depends, FastAPI
from fastapi_easy_versioning import versioning

v1_app = FastAPI(api_version=1)

# On an endpoint — via the decorator
@v1_app.get('/endpoint', dependencies=[Depends(versioning())])
def endpoint() -> None: ...

# Via add_api_route
v1_app.add_api_route('/added', endpoint, dependencies=[Depends(versioning(until=2))])

# On a whole router — every endpoint of the router is versioned
router = APIRouter(dependencies=[Depends(versioning())])

@router.get('/router-endpoint')
def router_endpoint() -> None: ...

v1_app.include_router(router)
```

## Reading Metadata Inside the Endpoint

The dependency can be injected into an endpoint — it then returns a `VersionInfo` named tuple with the route's resolved versioning configuration:

- `origin` — the version the endpoint is declared in;
- `until` — the last version the endpoint is available in. If `until` was not set explicitly, this is the latest existing API version.

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi_easy_versioning import VersionInfo, versioning

v1_app = FastAPI(api_version=1)

@v1_app.get('/endpoint')
def endpoint(version: Annotated[VersionInfo, Depends(versioning())]) -> str:
    return f"Available from version {version.origin} to version {version.until}"
```

Injection also works in WebSocket endpoints:

```python
from typing import Annotated

from fastapi import Depends, FastAPI, WebSocket
from fastapi_easy_versioning import VersionInfo, versioning

v1_app = FastAPI(api_version=1)

@v1_app.websocket('/ws')
async def ws_endpoint(
    websocket: WebSocket,
    version: Annotated[VersionInfo, Depends(versioning())],
) -> None:
    await websocket.accept()
    await websocket.send_text(f"Available since version {version.origin}")
    await websocket.close()
```

## Diagnostics

If versioning was not initialized, injecting `VersionInfo` raises a `RuntimeError` listing the possible causes:

- `VersioningMiddleware` is not added to the application that mounts the versions;
- the sub-application does not declare `FastAPI(api_version=<int>)`;
- the route was registered after the first request and `rebuild_versioning` was not called.
