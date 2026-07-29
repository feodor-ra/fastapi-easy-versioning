---
title: Limitations
---

# Limitations and internals

An honest list of what is out of scope — plus a little about how it works inside.

## FastAPI versions { #fastapi }

The dependency constraint is `fastapi >=0.95.0,!=0.137.0,!=0.137.1`.

| FastAPI version | Status | How routes are walked |
| --- | --- | --- |
| `0.95` – `0.136` | Supported | The flat `router.routes` list |
| `0.137.0`, `0.137.1` | **Excluded** | The route tree already exists, the public iterator does not |
| `0.137.2` and newer | Supported | The public `iter_route_contexts` |

FastAPI `0.137.0` refactored routing: `include_router` stopped copying routes and `router.routes` became a tree. The supported way to walk that tree — `iter_route_contexts` — only landed in `0.137.2`, so the two-release gap is excluded at the dependency level.

The right regime is picked automatically: the iterator is looked up with `getattr` at import time, and the flat walk is used when it is absent.

!!! info "What CI checks"

    The suite runs against the minimum supported (`0.95`), the last pre-refactor (`0.136`) and the latest FastAPI — on each of Python 3.10–3.14.

## Path-based versioning only

The library versions **mounted sub-applications**, which means a version is always expressed as a path prefix (`/v1`, `/api/public/v2`). Versioning by header (`Accept: application/vnd.api+json; version=2`), by query parameter or by subdomain is not supported: the version is determined by ASGI mount routing, before this library ever gets involved.

## Marking is mandatory

An endpoint without `Depends(versioning())` is invisible to versioning. This is deliberate — implicitly inheriting every route makes it far too easy for something unplanned to leak into a new version. The flip side: a forgotten marker looks like "the endpoint is somehow not inherited".

## When the build happens { #build-once }

Inheritance is built once, on the first ASGI event:

- under a real server that is the lifespan startup event;
- in tests over an ASGI transport (which skips lifespan) and for middleware on a *mounted* application, it is the first request.

Until then nothing is versioned: route copying happens at runtime, not at import or decoration time. Anything added afterwards needs an explicit [`rebuild_versioning`](middleware.md#runtime).

## `api_version` types

Only `int`, and `bool` is rejected separately despite being a subclass of it. Values like `"1"`, `1.0` or `True` make the sub-application ignored — with a `UserWarning`, so it does not look like a silently vanished version. A sub-application with no `api_version` at all is ignored silently: that is the normal way to mount something unversioned alongside.

## Shadowing and matching paths { #shadowing }

Inheritance into a version is skipped when it already has a route with the same path **and** the same methods. Two consequences follow:

- a `GET /items` in v2 does not shadow an inherited `POST /items` — those are different method sets;
- an HTTP route and a WebSocket route on the same path do not conflict at all: shadowing is kind-aware.

## WebSockets on fastapi 0.95 { #websocket }

In `0.95` `websocket()` has no `dependencies` parameter yet, so a WS route can only be marked through a dependency in the endpoint signature:

```python
@app_v1.websocket("/ws")
async def ws(
    websocket: WebSocket,
    version: Annotated[VersionInfo, Depends(versioning())],
) -> None: ...
```

On newer FastAPI both ways work. The tabbed recipe is in [Recipes](recipes.md#websocket).

## Copies of routes, not a shared object

Every inheriting version receives its own copy of the route. That is what keeps versions independent (`dependency_overrides` are resolved by the application of the version serving the request), but it also means modifying a route object in one version will not show up in the others — change the original route and call `rebuild_versioning`.

Routes coming from `include_router` are not copied but reconstructed from their effective context: copying them would lose the include-time prefix and the dependencies added at inclusion.
