from __future__ import annotations

import copy
from operator import itemgetter
from typing import TYPE_CHECKING, Final

from fastapi import FastAPI

# request_response must come from fastapi.routing, not starlette: it is the
# exact function APIRoute.__init__ builds its handler with (newer FastAPI
# ships its own copy that wires the dependencies' AsyncExitStack into scope).
from fastapi.routing import APIRoute, request_response
from starlette.applications import Starlette
from starlette.routing import Mount

from .dependency import VERSION_INFO_ATTR, VersionInfo, VersioningSupport

if TYPE_CHECKING:
    from collections.abc import Mapping  # pragma: no cover

    from starlette.types import ASGIApp, Receive, Scope, Send  # pragma: no cover

API_VERSION_KEY: Final = "api_version"


class VersioningMiddleware:
    """Middleware that provides and manages versioned APIs.

    Adds support for versioned APIs by mounting version-specific subapplications
    under a single FastAPI instance. On the first ASGI event it inherits versioned
    endpoints from older versions into newer ones and regenerates each version's
    OpenAPI schema. Requests themselves are routed by the mounts; use
    `rebuild_versioning` to pick up routes added at runtime.

    Usage:
        ```python
        from fastapi import FastAPI
        from fastapi.middleware import Middleware

        app = FastAPI(middleware=[Middleware(VersioningMiddleware)])
        # or alternatively
        app.add_middleware(VersioningMiddleware)
        ```
    """

    def __init__(self, app: ASGIApp, *, rebuild_openapi: bool = True) -> None:
        self.app = app
        self._rebuild_openapi = rebuild_openapi
        self._built = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._built and isinstance(app := scope.get("app"), Starlette):
            self._built = True
            rebuild_versioning(app, rebuild_openapi=self._rebuild_openapi)
        await self.app(scope, receive, send)


def rebuild_versioning(app: Starlette, *, rebuild_openapi: bool = True) -> None:
    """Build (or explicitly rebuild) versioned routes of an application.

    `VersioningMiddleware` calls this once on its first ASGI event. Call it
    manually to pick up routes or versions added at runtime after that.

    Args:
        app (Starlette): The application that directly mounts the version sub-apps.
        rebuild_openapi (bool, optional): Regenerate each version's OpenAPI schema
            after inheritance. Defaults to `True`.

    """
    version_mapping = _build_version_mapping(app)
    if not version_mapping:
        return

    for route, origin, until in _collect_versioned_routes(version_mapping):
        for version in range(origin + 1, until + 1):
            target = version_mapping.get(version)
            if target is None or _has_route(target, route):
                continue
            target.router.routes.append(_inherit_route(route, target))

    if not rebuild_openapi:
        return
    for version_app in version_mapping.values():
        version_app.openapi_schema = None
        version_app.openapi_schema = version_app.openapi()


def _has_route(app: FastAPI, route: APIRoute) -> bool:
    return any(
        isinstance(existing, APIRoute)
        and existing.path == route.path
        and existing.methods & route.methods
        for existing in app.router.routes
    )


def _inherit_route(route: APIRoute, target: FastAPI) -> APIRoute:
    inherited = copy.copy(route)
    inherited.dependency_overrides_provider = target
    inherited.app = request_response(inherited.get_route_handler())
    return inherited


def _build_version_mapping(app: Starlette) -> Mapping[int, FastAPI]:
    version_pairs = (
        (version, route.app)
        for route in app.routes
        if (
            isinstance(route, Mount)
            and isinstance(route.app, FastAPI)
            and isinstance(version := route.app.extra.get(API_VERSION_KEY), int)
            and not isinstance(version, bool)
        )
    )
    return dict(sorted(version_pairs, key=itemgetter(0)))


def _collect_versioned_routes(
    mapping: Mapping[int, FastAPI],
) -> list[tuple[APIRoute, int, int]]:
    max_version = max(mapping)

    collected = []
    for version, version_app in mapping.items():
        for route in version_app.routes:
            if not isinstance(route, APIRoute):
                continue

            supports = [
                dependency.call
                for dependency in route.dependant.dependencies
                if isinstance(dependency.call, VersioningSupport)
            ]
            if not supports:
                continue

            declared = [
                support.until for support in supports if support.until is not None
            ]
            until = min([*declared, max_version])
            previous = getattr(route, VERSION_INFO_ATTR, None)
            origin = previous.origin if isinstance(previous, VersionInfo) else version
            setattr(route, VERSION_INFO_ATTR, VersionInfo(origin=origin, until=until))

            collected.append((route, origin, until))
    return collected
