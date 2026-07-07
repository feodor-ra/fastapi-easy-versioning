# Versioning Dependency

!!! warning "The English documentation has been automatically translated. If you notice any grammatical or semantic errors, please help improve it by contributing corrections on [GitHub](https://github.com/feodor-ra/fastapi-easy-versioning), or refer to the original Russian documentation."

The `VersioningSupport` dependency and its factory `versioning` form the core mechanism for configuring and parameterizing API versioning.

The `versioning` factory allows you to specify the API version up to which an endpoint will be included in subsequent FastAPI sub-applications. If the factory is called without arguments or with `None`, the endpoint will be present in all future versions of the API.

## Using the Dependency

It is recommended to create the dependency through the `versioning` factory. The dependency can be added in all locations supported by the FastAPI interface.

```python
from fastapi import FastAPI, Depends
from fastapi_easy_versioning import versioning

v1_app = FastAPI(api_version=1)

@v1_app.get('/decorated-endpoint', dependencies=[Depends(versioning())])
def endpoint() -> None: ...

# Can also be added via the application's add_api_route method
v1_app.add_api_route('/app-add_api_route-call-endpoint', endpoint, dependencies=[Depends(versioning())])

# Or directly through the router
v1_app.router.add_api_route('/router-add_api_route-call-endpoint', endpoint, dependencies=[Depends(versioning())])
```

The dependency can be added to an entire router during initialization of a separate router or the whole FastAPI application. In this case, all endpoints added to it will participate in versioning according to the factory settings.

```python
from fastapi import FastAPI, Depends, APIRouter
from fastapi_easy_versioning import versioning

v1_app = FastAPI(api_version=1)
v2_app = FastAPI(api_version=2, dependencies=[Depends(versioning(until=2))])

router = APIRouter(dependencies=[Depends(versioning())])
v1_app.include_router(router)
```

## Accessing Dependency Data

The dependency can be injected into an endpoint using the `Annotated` syntax or the traditional dependency injection mechanism. The endpoint receives a `VersionInfo` named tuple with the route's resolved versioning configuration.

```python
from fastapi import FastAPI, Depends
from typing import Annotated
from fastapi_easy_versioning import VersionInfo, versioning

v1_app = FastAPI(api_version=1)

@v1_app.get('/endpoint')
def endpoint(version: Annotated[VersionInfo, Depends(versioning())]) -> str:
    return f"Available from version {version.origin} to version {version.until}"
```

`VersionInfo` fields:

- `origin` – the version number from which the endpoint was added
- `until` – the version number up to which the endpoint is available. If not specified explicitly, it will be set to the latest available API version.

Injection also works in WebSocket endpoints:

```python
from fastapi import FastAPI, Depends, WebSocket
from typing import Annotated
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

If `VersioningMiddleware` is not set up (or the route was not processed by versioning), injecting the data raises a `RuntimeError` describing the possible causes.
