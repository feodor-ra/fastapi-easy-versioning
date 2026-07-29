---
title: Quickstart
---

# Quickstart

In a few minutes: mount the versions, switch the middleware on, mark the endpoints and see the result in Swagger.

Versioning is built from two pieces that work **only together**:

- [`VersioningMiddleware`](guide/middleware.md) — added to the application that mounts the versions;
- [`versioning()`](guide/dependency.md) — the dependency that marks an endpoint as versioned.

## 1. Create the version applications

A version is an ordinary FastAPI application with an `api_version` extra. The value must be an integer; `0` is valid.

```python
from fastapi import FastAPI

app = FastAPI()
app_v1 = FastAPI(api_version=1)  # (1)!
app_v2 = FastAPI(api_version=2)

app.mount("/v1", app_v1)  # (2)!
app.mount("/v2", app_v2)
```

1. `api_version` is not a standard FastAPI parameter: unknown keyword arguments land in `app.extra`, which is where the middleware reads it from.
2. The mount prefix is arbitrary — versions are told apart by `api_version`, not by path.

## 2. Add the middleware

The middleware goes on the **aggregating** application — the one that directly mounts the versions. Not on the versions themselves.

=== "add_middleware"

    ```python
    app.add_middleware(VersioningMiddleware)
    ```

=== "at construction time"

    ```python
    from fastapi import middleware

    app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware)])
    ```

!!! warning "On the aggregating application only"

    Added to `app_v1` itself, the middleware will find no versions at all: it looks for them among the applications mounted directly under it.

## 3. Mark the endpoints

Versioning is **opt-in**. An endpoint without the `versioning()` dependency stays in its own version and takes no part in inheritance whatsoever.

```python
from fastapi import Depends


@app_v1.get("/only-v1", dependencies=[Depends(versioning(until=1))])
def only_v1() -> str:
    return "Available only in version v1"


@app_v1.get("/all-versions", dependencies=[Depends(versioning())])  # (1)!
def all_versions() -> str:
    return "Available in all versions starting from v1"


@app_v2.get("/from-v2", dependencies=[Depends(versioning())])
def from_v2() -> str:
    return "Available starting from v2 and in all future versions"
```

1. `versioning()` without `until` means "through the latest version", not "in this one only". A common source of surprise.

## 4. Check the result

```bash
uvicorn main:app
```

| Request | Result |
| --- | --- |
| `GET /v1/only-v1` | 200 — declared in v1 |
| `GET /v2/only-v1` | 404 — capped by `until=1` |
| `GET /v1/all-versions` | 200 — declared in v1 |
| `GET /v2/all-versions` | 200 — inherited into v2 |
| `GET /v1/from-v2` | 404 — the endpoint only appeared in v2 |
| `GET /v2/from-v2` | 200 |

`/v1/docs` and `/v2/docs` show exactly what the version actually serves: the OpenAPI schema is regenerated after inheritance.

## 5. Read the version metadata

The same dependency can be injected into the signature — then it yields a `VersionInfo` with the resolved bounds of the range:

```python
from typing import Annotated

from fastapi_easy_versioning import VersionInfo


@app_v1.get("/where-am-i")
def where_am_i(version: Annotated[VersionInfo, Depends(versioning())]) -> str:
    return f"Available from v{version.origin} through v{version.until}"
```

`until` here is already resolved: with no explicit cap it is the number of the latest mounted version.

## Next

- [The `versioning` dependency](guide/dependency.md) — every way to mark endpoints, and error diagnostics.
- [Middleware](guide/middleware.md) — inheritance rules, OpenAPI, adding routes at runtime.
- [Recipes](guide/recipes.md) — versioning a whole router, several independent APIs, WebSockets.
- [Limitations](guide/limitations.md) — FastAPI version compatibility and the boundaries of the approach.
