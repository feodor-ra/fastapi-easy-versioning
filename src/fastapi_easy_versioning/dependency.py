# No `from __future__ import annotations` here: FastAPI resolves the
# annotations of `VersioningSupport.__call__` at runtime; callable instances
# carry no `__globals__` to evaluate postponed annotations against.
from typing import Final, NamedTuple

from fastapi.requests import HTTPConnection

VERSION_INFOS_ATTR: Final = "_fastapi_easy_versioning_infos"
"""Attribute on a version app's `state` holding `dict[int, VersionInfo]`
keyed by `id()` of the route object (routes are shared between versions
since the FastAPI 0.137 router-tree refactor and are not hashable)."""


class VersionInfo(NamedTuple):
    """Resolved versioning metadata of an endpoint.

    Yielded by the [`versioning`][fastapi_easy_versioning.versioning] dependency
    when it is injected into an endpoint signature. Both fields are resolved by
    the middleware against the actually mounted versions, so `until` is a
    concrete version number even when the endpoint declared none.

    Usage:
        ```python
        @app_v1.get("/endpoint")
        def endpoint(version: Annotated[VersionInfo, Depends(versioning())]) -> str:
            return f"available from v{version.origin} through v{version.until}"
        ```
    """

    origin: int
    """The version that declared the endpoint."""

    until: int
    """The last version the endpoint is available in.

    When no `until` was declared, this is the latest mounted version at the time
    versioning was built.
    """


class VersioningSupport:
    """Callable dependency marking an endpoint as versioned.

    Instances are produced by [`versioning`][fastapi_easy_versioning.versioning]
    and are meant to be passed to `Depends()`; construct them through that
    factory rather than directly. An instance only carries the *declared* `until`
    and is never mutated — the resolved per-route metadata lives in a registry on
    the version sub-app, so the same instance can safely be shared by a router
    included into several versions.

    Args:
        until (int | None, optional): The last supported version, as declared at
            the call site. Defaults to `None`.

    """

    def __init__(self, *, until: int | None = None) -> None:
        self.until = until

    async def __call__(self, connection: HTTPConnection) -> VersionInfo:
        """Resolve the versioning metadata of the route being served.

        Args:
            connection (HTTPConnection): The current connection, injected by
                FastAPI for both HTTP requests and WebSocket connections.

        Returns:
            VersionInfo: The `origin`/`until` pair resolved for this route.

        Raises:
            RuntimeError: The route was never processed by the middleware — see
                [`rebuild_versioning`][fastapi_easy_versioning.rebuild_versioning].

        """
        state = getattr(connection.scope.get("app"), "state", None)
        infos: dict[int, VersionInfo] | None = getattr(state, VERSION_INFOS_ATTR, None)
        info = (
            infos.get(id(connection.scope.get("route"))) if infos is not None else None
        )
        if info is None:
            msg = (
                "Versioning is not initialized for this route. Make sure that "
                "VersioningMiddleware is added to the application that mounts "
                "the version sub-apps, the sub-app is created with "
                "FastAPI(api_version=<int>), and the route is registered before "
                "the first request (otherwise call rebuild_versioning)."
            )
            raise RuntimeError(msg)
        return info


def versioning(*, until: int | None = None) -> VersioningSupport:
    """Dependency factory to mark endpoints as versioned.

    Marking is opt-in: an endpoint without this dependency is invisible to
    versioning and stays only in the version that declares it. Inheritance itself
    is performed by
    [`VersioningMiddleware`][fastapi_easy_versioning.VersioningMiddleware].

    Usage:
        ```python
        @router.get("/path", dependencies=[Depends(versioning(until=...))])
        def endpoint():
            ...

        # Apply versioning to all endpoints in the router
        router = APIRouter(dependencies=[Depends(versioning(until=...))])
        router.add_api_route("/path", endpoint)

        # Or inject versioning metadata into the endpoint
        @router.get("/path")
        def endpoint(data: Annotated[VersionInfo, Depends(versioning())]):
            from_version = data.origin
            end_supported_version = data.until
        ```

    Args:
        until (int | None, optional): The last version the endpoint is available
            in, inclusive. If `None`, the endpoint remains available through the
            latest version — including versions mounted later. When a route
            carries several versioning dependencies (say one on the router and
            one on the endpoint), the smallest declared `until` wins. An `until`
            below the declaring version emits a `UserWarning`: the endpoint is
            then inherited nowhere. Defaults to `None`.

    Returns:
        VersioningSupport:
            A dependency callable compatible with FastAPI's `Depends()`. Injected
            into an endpoint signature, it yields a
            [`VersionInfo`][fastapi_easy_versioning.VersionInfo].

    """
    return VersioningSupport(until=until)
