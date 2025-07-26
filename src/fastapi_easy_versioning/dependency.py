from __future__ import annotations

from typing import Any, Callable

from typing_extensions import Self


class VersioningSupport:
    def __init__(self, *, until: int | None = None) -> None:
        self.origin: int | None = None
        self.until = until

    def __call__(self) -> Self:
        if self.until is None or self.origin is None:
            msg = "VersioningMiddleware not used"
            raise RuntimeError(msg)
        return self


def versioning(*, until: int | None = None) -> Callable[..., Any]:
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
        def endpoint(data: Annotated[VersioningSupport, Depends(versioning())]):
            from_version = data.origin
            end_supported_version = data.until
        ```

    Args:
        until (int | None, optional): The last supported version. If `None`,
            the endpoint remains available in all versions. Defaults to `None`.

    Returns:
        function (Callable[..., Any]):
            A dependency callable compatible with FastAPI's `Depends()`.

    """
    return VersioningSupport(until=until)
