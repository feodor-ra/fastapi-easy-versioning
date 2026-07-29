---
title: Middleware
---

# Middleware

`VersioningMiddleware` does the core work of versioning: it finds the version sub-applications, inherits the marked endpoints from older versions into newer ones and rebuilds each version's OpenAPI schema.

## Where to add it

The middleware is added only to the application that **directly mounts** the version sub-applications — never to the versions themselves.

```python
from fastapi import FastAPI
from fastapi_easy_versioning import VersioningMiddleware

app = FastAPI()
app_v1 = FastAPI(api_version=1)
app_v2 = FastAPI(api_version=2)

app.mount("/v1", app_v1)
app.mount("/v2", app_v2)
app.add_middleware(VersioningMiddleware)
```

For two or more isolated versioned APIs, add a separate `VersioningMiddleware` to each aggregating application — every instance versions only the sub-applications mounted directly under its own app:

```python
from fastapi import FastAPI, middleware
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

Version numbering of such APIs is independent: `public_v1` and `private_v1` are different sets and never inherit from each other. A full walkthrough is in the [example](../examples/multiple.md).

## Configuring the version applications { #api-version }

The middleware decides which FastAPI applications take part in versioning by the `api_version` extra (the `API_VERSION_KEY` constant):

- `api_version` must be an integer; version `0` is valid.
- A sub-application without `api_version` is ignored: endpoints are neither inherited into it nor taken from it, even when marked with the `versioning()` dependency.
- An `api_version` of the wrong type (`"1"`, `True`, `1.0`) makes the sub-application ignored, and a `UserWarning` is emitted so the typo does not go unnoticed.

```python
app_v1 = FastAPI(api_version=1)   # takes part in versioning
internal = FastAPI()              # ignored
```

!!! note "`bool` is not `int`"

    Even though `True == 1` in Python, `api_version=True` counts as a type error: it is far more likely to be a typo than an intentional version number.

## How inheritance works { #inheritance }

Inheritance is built **once** — on the first ASGI event. Under a real server (uvicorn) that is the lifespan startup event; when the middleware sits on an application mounted inside another one, or in tests, it is the first request. Subsequent requests do no extra work.

```mermaid
graph LR
    A["First ASGI event"] --> B["Discover versions<br/>by api_version"]
    B --> C["Select routes<br/>with versioning()"]
    C --> D["Resolve until"]
    D --> E["Copy routes into<br/>versions origin+1..until"]
    E --> F["Regenerate<br/>OpenAPI schemas"]
```

The rules:

- Only endpoints marked with `versioning()` are inherited, over the range from the declaring version through `until`, inclusive.
- Every inheriting version receives its **own copy** of the route: changing a route in one version does not affect the others, and `dependency_overrides` are resolved by the application of the version serving the request.
- If a newer version declares its own endpoint with the same path and methods, inheritance into it is skipped — the newer version **shadows** the older one, at runtime and in the OpenAPI schema alike.
- Both HTTP endpoints (`APIRoute`) and WebSocket endpoints (`APIWebSocketRoute`) are versioned, with identical semantics. Shadowing is kind-aware: an HTTP endpoint and a WebSocket on the same path do not interfere.

!!! warning "A fastapi 0.95 caveat"

    WebSocket routes have no route-level `dependencies` parameter there, so the only way to mark them is a dependency in the endpoint signature. See [Limitations](limitations.md#websocket).

## OpenAPI { #openapi }

After inheritance the middleware rebuilds each version's OpenAPI schema, so every version's `/docs` shows both its own and its inherited endpoints.

The rebuild can be switched off with the `rebuild_openapi` parameter. Endpoints are still inherited and served, but the inherited ones do not appear in that version's schema and `/docs`:

```python
from fastapi import FastAPI, middleware
from fastapi_easy_versioning import VersioningMiddleware

app = FastAPI(
    middleware=[middleware.Middleware(VersioningMiddleware, rebuild_openapi=False)]
)

# or

app = FastAPI()
app.add_middleware(VersioningMiddleware, rebuild_openapi=False)
```

## Adding endpoints at runtime { #runtime }

A versioned endpoint or a new version added after the first request is not picked up automatically. That is what the public `rebuild_versioning` function is for: it rebuilds the inheritance and refreshes the versions' OpenAPI schemas. The call is idempotent, and a default `until` is re-resolved against the new latest version.

```python
from fastapi_easy_versioning import rebuild_versioning

# after adding routes or mounting a new version at runtime
rebuild_versioning(app)  # app is the application that mounts the versions
```

## FastAPI compatibility

In short: `0.95` and newer are supported, except `0.137.0` and `0.137.1`. The reasoning and the matrix of routing regimes are in [Limitations](limitations.md#fastapi).

!!! tip "Full reference"

    Signatures and detailed descriptions live in the [API reference](../reference/middleware.md).
