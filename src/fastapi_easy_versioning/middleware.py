from __future__ import annotations

import copy
from operator import itemgetter
from typing import TYPE_CHECKING, Any, Final, NamedTuple
import warnings

from fastapi import FastAPI
import fastapi.routing

# request_response must come from fastapi.routing, not starlette: it is the
# exact function APIRoute.__init__ builds its handler with (newer FastAPI
# ships its own copy that wires the dependencies' AsyncExitStack into scope).
from fastapi.routing import APIRoute, request_response
from starlette.applications import Starlette
from starlette.routing import Mount

from .dependency import VERSION_INFOS_ATTR, VersionInfo, VersioningSupport

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping  # pragma: no cover

    from starlette.types import ASGIApp, Receive, Scope, Send  # pragma: no cover

API_VERSION_KEY: Final = "api_version"

# Public route-tree iteration API. Since the 0.137 router refactor
# include_router no longer copies routes into a flat list: router.routes
# holds private tree nodes and iter_route_contexts (fastapi >= 0.137.2) is
# the supported way to walk them. On older FastAPI the attribute is absent
# and the flat scan below is used instead.
_iter_route_contexts: Callable[..., Any] | None = getattr(
    fastapi.routing, "iter_route_contexts", None
)


class _RouteView(NamedTuple):
    """An APIRoute observed in a version app, with its effective properties."""

    route: APIRoute
    """Original route object (what scope["route"] holds at request time)."""

    path: str
    methods: set[str]
    dependant: Any
    context: Any
    """RouteContext the route was found through (None on pre-tree FastAPI)."""


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

    for view, origin, until in _collect_versioned_routes(version_mapping):
        for version in range(origin + 1, until + 1):
            target = version_mapping.get(version)
            if target is None or _has_route(target, view):
                continue
            inherited = _inherit_route(view, target)
            _infos_of(target)[id(inherited)] = VersionInfo(origin=origin, until=until)
            target.router.routes.append(inherited)

    if not rebuild_openapi:
        return
    for version_app in version_mapping.values():
        version_app.openapi_schema = None
        version_app.openapi_schema = version_app.openapi()


def _iter_api_routes(app: FastAPI) -> Iterator[_RouteView]:
    if _iter_route_contexts is None:  # pragma: no cover - fastapi < 0.137.2
        for route in app.routes:
            if isinstance(route, APIRoute):
                yield _RouteView(
                    route, route.path, set(route.methods or ()), route.dependant, None
                )
        return
    for context in _iter_route_contexts(app.router.routes):
        route = context.original_route
        if isinstance(route, APIRoute):
            yield _RouteView(
                route,
                context.path,
                set(context.methods or ()),
                context.dependant,
                context,
            )


def _has_route(app: FastAPI, view: _RouteView) -> bool:
    return any(
        existing.path == view.path and existing.methods & view.methods
        for existing in _iter_api_routes(app)
    )


def _inherit_route(view: _RouteView, target: FastAPI) -> APIRoute:
    route, context = view.route, view.context
    if context is None or (
        context.path == route.path and context.dependant is route.dependant
    ):
        # The route is served as-is (no include-time prefix/dependencies
        # applied on top), so a shallow copy keeps everything.
        inherited = copy.copy(route)
        inherited.dependency_overrides_provider = target
        inherited.app = request_response(inherited.get_route_handler())
        return inherited
    # The route comes from an included router: copying the original would
    # lose the include context (prefix, dependencies, tags, ...), so build
    # a standalone route from the effective properties instead.
    return APIRoute(
        path=context.path,
        endpoint=context.endpoint,
        response_model=context.response_model,
        status_code=context.status_code,
        tags=list(context.tags or []),
        dependencies=list(context.dependencies or []),
        summary=context.summary,
        description=context.description,
        response_description=context.response_description,
        responses=dict(context.responses or {}),
        deprecated=context.deprecated,
        methods=sorted(context.methods or ()),
        operation_id=context.operation_id,
        response_model_include=context.response_model_include,
        response_model_exclude=context.response_model_exclude,
        response_model_by_alias=context.response_model_by_alias,
        response_model_exclude_unset=context.response_model_exclude_unset,
        response_model_exclude_defaults=context.response_model_exclude_defaults,
        response_model_exclude_none=context.response_model_exclude_none,
        include_in_schema=context.include_in_schema,
        response_class=context.response_class,
        name=context.name,
        callbacks=context.callbacks,
        openapi_extra=context.openapi_extra,
        generate_unique_id_function=context.generate_unique_id_function,
        dependency_overrides_provider=target,
    )


def _infos_of(app: FastAPI) -> dict[int, VersionInfo]:
    infos = getattr(app.state, VERSION_INFOS_ATTR, None)
    if infos is None:
        infos = {}
        setattr(app.state, VERSION_INFOS_ATTR, infos)
    return infos


def _build_version_mapping(app: Starlette) -> Mapping[int, FastAPI]:
    version_pairs = []
    for route in app.routes:
        if not (
            isinstance(route, Mount)
            and isinstance(route.app, FastAPI)
            and API_VERSION_KEY in route.app.extra
        ):
            continue
        version = route.app.extra[API_VERSION_KEY]
        if isinstance(version, int) and not isinstance(version, bool):
            version_pairs.append((version, route.app))
        else:
            warnings.warn(
                f"Mounted app at {route.path!r} declares "
                f"{API_VERSION_KEY}={version!r}, which is not an int; "
                "the app is ignored by versioning.",
                stacklevel=2,
            )
    return dict(sorted(version_pairs, key=itemgetter(0)))


def _collect_versioned_routes(
    mapping: Mapping[int, FastAPI],
) -> list[tuple[_RouteView, int, int]]:
    max_version = max(mapping)

    collected = []
    for version, version_app in mapping.items():
        infos = _infos_of(version_app)
        for view in _iter_api_routes(version_app):
            supports = [
                dependency.call
                for dependency in view.dependant.dependencies
                if isinstance(dependency.call, VersioningSupport)
            ]
            if not supports:
                continue

            declared = [
                support.until for support in supports if support.until is not None
            ]
            until = min([*declared, max_version])
            previous = infos.get(id(view.route))
            origin = previous.origin if previous is not None else version
            if until < origin:
                warnings.warn(
                    f"Route {view.path!r} is declared in version {origin} "
                    f"but versioned until={until}; it will not be inherited "
                    "anywhere.",
                    stacklevel=2,
                )
            infos[id(view.route)] = VersionInfo(origin=origin, until=until)

            collected.append((view, origin, until))
    return collected
