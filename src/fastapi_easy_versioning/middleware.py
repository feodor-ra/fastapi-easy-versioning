from __future__ import annotations

from functools import reduce
from itertools import tee
from operator import itemgetter
from typing import TYPE_CHECKING, Final

from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from starlette.applications import Starlette
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.routing import Mount

from .dependency import VersioningSupport

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping  # pragma: no cover

    from starlette.requests import Request  # pragma: no cover
    from starlette.responses import Response  # pragma: no cover
    from starlette.types import ASGIApp, Receive, Scope, Send  # pragma: no cover

API_VERSION_KEY: Final = "api_version"


class VersioningMiddleware(BaseHTTPMiddleware):
    """Middleware that provides and manages versioned APIs.

    Adds support for versioned routing by mounting version-specific subapplications
    under a single FastAPI instance. This middleware enables serving multiple
    API versions through a unified entry point by inspecting the request path to route
    requests to the appropriate version.

    Usage:
        ```python
        from fastapi import FastAPI
        from fastapi.middleware import Middleware

        app = FastAPI(middleware=[Middleware(VersioningMiddleware)])
        # or alternatively
        app.add_middleware(VersioningMiddleware)
        ```
    """

    def __init__(
        self,
        app: ASGIApp,
        dispatch: DispatchFunction | None = None,
    ) -> None:
        super().__init__(app, dispatch)
        self._latest_setup_routes = set[str]()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if isinstance(app := scope.get("app"), Starlette):
            self._build_versioning_routes(app)
        return await super().__call__(scope, receive, send)

    def _build_versioning_routes(self, root_app: Starlette) -> None:
        version_mapping = _build_version_mapping(root_app)
        version_routes, for_check = tee(_search_routes(version_mapping))
        hashes = {route.unique_id for route, *_ in for_check}
        if self._latest_setup_routes == hashes:
            return

        routes = (
            (route, version)
            for route, min_version, max_version in version_routes
            for version in range(min_version, max_version + 1)
        )
        for route, version in routes:
            if not (app := version_mapping.get(version)):
                continue
            if route not in app.router.routes:
                app.router.routes.append(route)
        for app in version_mapping.values():
            app.openapi_schema = app.openapi()
        self._latest_setup_routes = hashes

    @staticmethod
    async def dispatch(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        return await call_next(request)


def _build_version_mapping(app: Starlette) -> Mapping[int, FastAPI]:
    version_pairs = (
        (version, route.app)
        for route in app.routes
        if (
            isinstance(route, Mount)
            and isinstance(route.app, FastAPI)
            and isinstance(version := route.app.extra.get(API_VERSION_KEY), int)
        )
    )
    return dict(sorted(version_pairs, key=itemgetter(0)))


def _search_routes(
    mapping: Mapping[int, FastAPI],
) -> Iterable[tuple[APIRoute, int, int]]:
    max_version = max(mapping)

    routes = (
        (version, route)
        for version, app in mapping.items()
        for route in app.routes
        if isinstance(route, APIRoute)
    )

    for version, route in routes:
        dependencies = [
            dependency.call
            for dependency in route.dependant.dependencies
            if isinstance(dependency.call, VersioningSupport)
        ]
        if not dependencies:
            continue

        until = reduce(
            lambda acc, item: min(item, acc) if item is not None else acc,
            (item.until for item in dependencies),
            max_version,
        )

        for dependency in dependencies:
            dependency.until = dependency.until or until
            dependency.origin = dependency.origin or version
            yield (route, version, until)
