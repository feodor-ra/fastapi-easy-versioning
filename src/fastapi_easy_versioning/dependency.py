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
    """Resolved versioning metadata of an endpoint."""

    origin: int
    """The version that declared the endpoint."""

    until: int
    """The last version the endpoint is available in."""


class VersioningSupport:
    def __init__(self, *, until: int | None = None) -> None:
        self.until = until

    async def __call__(self, connection: HTTPConnection) -> VersionInfo:
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
        until (int | None, optional): The last supported version. If `None`,
            the endpoint remains available in all versions. Defaults to `None`.

    Returns:
        VersioningSupport:
            A dependency callable compatible with FastAPI's `Depends()`.

    """
    return VersioningSupport(until=until)
