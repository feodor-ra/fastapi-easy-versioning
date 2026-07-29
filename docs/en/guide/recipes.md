---
title: Recipes
---

# Recipes

Ready-made patterns for common tasks.

## Version a whole router

A dependency attached to an `APIRouter` covers every endpoint of it — there is no need to mark them one by one.

```python
from fastapi import APIRouter, Depends, FastAPI
from fastapi_easy_versioning import versioning

users = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(versioning())])


@users.get("")
def list_users() -> list[User]: ...


@users.get("/{user_id}")
def get_user(user_id: int) -> User: ...


app_v1.include_router(users)
```

The same router can be included into several versions — the declaring version of each set of routes is the application it was included into.

!!! tip "Cap a whole router"

    `APIRouter(dependencies=[Depends(versioning(until=2))])` caps every endpoint of the router at once. If a particular endpoint declares its own `until`, [the smaller of the two](dependency.md#until) applies.

## Keep an endpoint out of versioning

The inverse task is solved by not marking it: internal and service handlers simply never get `versioning()`.

```python
@app_v1.get("/healthz")  # (1)!
def healthz() -> str:
    return "ok"
```

1. Stays in v1 only. It reaches no other version and appears in no other version's schema.

## Replace an endpoint in a newer version

Just declare your own endpoint on the same path in the newer version: inheritance into it is skipped, while the old implementation keeps serving the older versions.

```python
@app_v1.get("/profile", dependencies=[Depends(versioning())])
def profile_v1() -> ProfileV1: ...


@app_v3.get("/profile", dependencies=[Depends(versioning())])  # (1)!
def profile_v3() -> ProfileV3: ...
```

1. v1 and v2 serve the old shape, v3 and everything after it the new one. Only the new response schema reaches `/v3/docs`.

## Add a version while the application runs

Inheritance is built once, so a version mounted later needs an explicit rebuild.

```python
from fastapi_easy_versioning import rebuild_versioning

app_v3 = FastAPI(api_version=3)
app.mount("/v3", app_v3)

rebuild_versioning(app)  # (1)!
```

1. The call is idempotent: it creates no duplicates for already inherited routes, but it does re-resolve the default `until` — "through the latest version" now means v3.

The same applies after an `include_router` or `add_api_route` on an already running application. See [the runtime section](middleware.md#runtime).

## Two independent APIs in one application

Each aggregating application gets its own middleware — and its own independent version numbering.

```python
app = FastAPI()

public_app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware)])
private_app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware)])

app.mount("/api/public", public_app)
app.mount("/api/private", private_app)

public_app.mount("/v1", FastAPI(api_version=1))
private_app.mount("/v1", FastAPI(api_version=1))
```

A full walkthrough is in the [example](../examples/multiple.md).

## Version a WebSocket { #websocket }

WebSocket routes are versioned on par with HTTP — same `until` semantics, same shadowing. Only the way to mark them differs:

=== "fastapi ≥ 0.100"

    ```python
    @app_v1.websocket("/ws", dependencies=[Depends(versioning())])
    async def ws(websocket: WebSocket) -> None: ...
    ```

=== "fastapi 0.95"

    ```python
    @app_v1.websocket("/ws")  # (1)!
    async def ws(
        websocket: WebSocket,
        version: Annotated[VersionInfo, Depends(versioning())],
    ) -> None: ...
    ```

    1. `websocket()` has no `dependencies` parameter in 0.95 — the marking goes into the endpoint signature.

## Hide inherited endpoints from Swagger

If inherited routes should be served but not shown in the newer versions' `/docs`, switch the schema rebuild off:

```python
app.add_middleware(VersioningMiddleware, rebuild_openapi=False)
```

Every version keeps the schema FastAPI assembled from its own routes.

## Report the version range to the client

`VersionInfo` is available in an endpoint as an ordinary dependency — handy for putting the support range into a response header:

```python
@app_v1.get("/items", dependencies=[Depends(versioning())])
def items(version: Annotated[VersionInfo, Depends(versioning())]) -> Response:
    return JSONResponse(
        get_items(),
        headers={"X-API-Deprecated-After": str(version.until)},
    )
```
