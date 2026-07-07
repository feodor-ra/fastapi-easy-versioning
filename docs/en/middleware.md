# Middleware

The `VersioningMiddleware` handles the core functionality of API versioning.

The middleware is added only to the FastAPI application that aggregates sub-applications responsible for specific versions.

```python
from fastapi import FastAPI, Depends
from fastapi_easy_versioning import VersioningMiddleware, versioning

app = FastAPI()
app_v1 = FastAPI(api_version=1)
app_v2 = FastAPI(api_version=2)

app.mount("/v1", app_v1)
app.mount("/v2", app_v2)
app.add_middleware(VersioningMiddleware)
```

If you need to create two or more isolated versioned APIs that should operate independently, you should add `VersioningMiddleware` to each such aggregating application.

```python
from fastapi import Depends, FastAPI, middleware
from fastapi_easy_versioning import VersioningMiddleware

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
```

## Versioned Applications Configuration

The middleware identifies which FastAPI applications participate in versioning using the `api_version` extra parameter (the `API_VERSION_KEY` constant). If an application doesn't have this parameter, it will be ignored during versioning: endpoints won't be added to it, and endpoints won't be taken from it, even if they were correctly marked with the `VersioningSupport` dependency. If `api_version` is present but is not an integer (for example, `"1"` or `True`), the application is also ignored and a `UserWarning` is emitted.

## Middleware Operation

The middleware builds versioning once — on its first ASGI event (under a real server that is the lifespan startup event; when mounted inside another application or in tests it is the first request). Endpoints of older versions are copied into subsequent sub-applications according to their versioning settings, and each version's OpenAPI schema is rebuilt. Subsequent requests perform no additional work.

Each version receives its own copy of the route:

- mutating a route in one version does not affect other versions;
- `dependency_overrides` are resolved by the application of the version serving the request;
- if a newer version declares its own endpoint with the same path and methods, inheritance into it is skipped — the newer version shadows the older one both at runtime and in the OpenAPI schema.

Both HTTP endpoints (`APIRoute`) and WebSocket endpoints (`APIWebSocketRoute`) are versioned with the same semantics (`until`, `origin`, shadowing, `rebuild_versioning`). Shadowing is kind-aware: an HTTP endpoint and a websocket on the same path do not conflict. A fastapi 0.95 nuance: WebSocket routes there have no `dependencies` parameter yet, so they can only be marked for versioning with a dependency in the endpoint signature.

If you need to disable rebuilding the OpenAPI schema, you can do this when configuring the middleware by passing the `rebuild_openapi` parameter:

```python
from fastapi import Depends, FastAPI, middleware
from fastapi_easy_versioning import VersioningMiddleware

app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware, rebuild_openapi=False)])

# or

app = FastAPI()
app.add_middleware(VersioningMiddleware, rebuild_openapi=False)
```

## FastAPI Compatibility

- **FastAPI below 0.137** — supported: routes are walked via the flat `router.routes` list.
- **FastAPI 0.137.0 and 0.137.1** — **excluded** by the package's dependency constraints: these versions already contain the routing refactor (`include_router` no longer copies routes, `router.routes` became a tree), but the public `iter_route_contexts` iteration API only appeared in 0.137.2.
- **FastAPI 0.137.2 and newer** — supported: routes are walked via the public `iter_route_contexts`, so endpoints registered through `include_router` are versioned correctly, including include-time prefixes and dependencies.

Compatibility is checked in CI against the minimum supported (0.95), the last pre-refactor (0.136) and the latest FastAPI versions.

## Adding Endpoints at Runtime

A versioned endpoint or a new version added after the first request will not be picked up automatically. The public `rebuild_versioning` function exists for this: it rebuilds the inheritance and refreshes the versions' OpenAPI schemas.

```python
from fastapi_easy_versioning import rebuild_versioning

# after adding routes or mounting a new version at runtime
rebuild_versioning(app)  # app is the application that mounts the versions
```
