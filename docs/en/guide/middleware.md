# Middleware

`VersioningMiddleware` does the core work of versioning: it finds the version sub-applications, inherits the marked endpoints from older versions into newer ones and rebuilds each version's OpenAPI schema.

## Where to Add It

The middleware is added only to the application that **directly mounts** the version sub-applications — not to the versions themselves.

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

If you need two or more isolated versioned APIs, add a separate `VersioningMiddleware` to each aggregating application — every instance versions only the sub-applications mounted directly under its own application:

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

The middleware identifies which FastAPI applications participate in versioning by the `api_version` extra parameter (the `API_VERSION_KEY` constant):

- `api_version` must be an integer; version `0` is valid.
- A sub-application without `api_version` is ignored: endpoints are neither inherited into it nor taken from it, even when marked with the `versioning()` dependency.
- An `api_version` of a wrong type (`"1"`, `True`, `1.0`) — the sub-application is also ignored and a `UserWarning` is emitted, so a typo does not go unnoticed.

```python
app_v1 = FastAPI(api_version=1)   # participates in versioning
internal = FastAPI()              # ignored
```

## How Inheritance Works

Inheritance is built **once** — on the first ASGI event. Under a real server (uvicorn) that is the lifespan startup event; when mounted inside another application or in tests it is the first request. Subsequent requests perform no additional work.

The rules:

- Only endpoints marked with `versioning()` are inherited, in the range from the declaring version up to and including `until`.
- Every inheriting version receives its **own copy** of the route: mutating a route in one version does not affect the others, and `dependency_overrides` are resolved by the application of the version serving the request.
- If a newer version declares its own endpoint with the same path and methods, inheritance into it is skipped — the newer version **shadows** the older one both at runtime and in the OpenAPI schema.
- Both HTTP endpoints (`APIRoute`) and WebSocket endpoints (`APIWebSocketRoute`) are versioned with the same semantics. Shadowing is kind-aware: an HTTP endpoint and a websocket on the same path do not conflict. A fastapi 0.95 nuance: WebSocket routes there have no `dependencies` parameter yet, so they can only be marked for versioning with a dependency in the endpoint signature.

## OpenAPI

After inheritance the middleware rebuilds each version's OpenAPI schema, so every version's `/docs` shows both its own and its inherited endpoints.

The rebuild can be disabled with the `rebuild_openapi` parameter. Endpoints are still inherited and served, but the inherited ones will not appear in the corresponding version's schema and `/docs`:

```python
from fastapi import Depends, FastAPI, middleware
from fastapi_easy_versioning import VersioningMiddleware

app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware, rebuild_openapi=False)])

# or

app = FastAPI()
app.add_middleware(VersioningMiddleware, rebuild_openapi=False)
```

## Adding Endpoints at Runtime

A versioned endpoint or a new version added after the first request will not be picked up automatically. The public `rebuild_versioning` function exists for this: it rebuilds the inheritance and refreshes the versions' OpenAPI schemas. The call is idempotent, and a default `until` is re-resolved against the new latest version.

```python
from fastapi_easy_versioning import rebuild_versioning

# after adding routes or mounting a new version at runtime
rebuild_versioning(app)  # app is the application that mounts the versions
```

## FastAPI Compatibility

- **FastAPI below 0.137** — supported: routes are walked via the flat `router.routes` list.
- **FastAPI 0.137.0 and 0.137.1** — **excluded** by the package's dependency constraints: these versions already contain the routing refactor (`include_router` no longer copies routes, `router.routes` became a tree), but the public `iter_route_contexts` iteration API only appeared in 0.137.2.
- **FastAPI 0.137.2 and newer** — supported: routes are walked via the public `iter_route_contexts`, so endpoints registered through `include_router` are versioned correctly, including include-time prefixes and dependencies.

Compatibility is checked in CI against the minimum supported (0.95), the last pre-refactor (0.136) and the latest FastAPI versions.
