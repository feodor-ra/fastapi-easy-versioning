# CLAUDE.md

A small FastAPI library (`fastapi-easy-versioning`, PyPI) for building versioned APIs. You mount one FastAPI sub-app per version under the root app; the library automatically inherits endpoints from older versions into newer ones and regenerates each version's OpenAPI schema. Runtime dep is only `fastapi>=0.95.0`; supports Python 3.10–3.14. src-layout, fully typed (ships `py.typed`).

## Architecture / how it works

Public API is exactly six names re-exported from the package root (keep `src/fastapi_easy_versioning/__init__.py` `__all__` in sync with docs): `API_VERSION_KEY`, `VersionInfo`, `VersioningMiddleware`, `VersioningSupport`, `rebuild_versioning`, `versioning`.

Two pieces must be used **together**:
- **`VersioningMiddleware`** — added ONLY to an aggregating app that mounts the version sub-apps, never to the sub-apps themselves. Multiple instances are supported: each attaches to an app that *directly* mounts a version set (see `examples/multiple_versioning.py` — `public_app`/`private_app`, themselves mounted under the root `app`), so independent APIs version separately.
- **`versioning(*, until=None)`** — dependency factory marking an endpoint (or a whole `APIRouter(dependencies=[...])`) as versioned. `until` is keyword-only.

Key files:
- `src/fastapi_easy_versioning/__init__.py` — re-exports the 6 public names.
- `src/fastapi_easy_versioning/dependency.py` — `versioning()` returns a `VersioningSupport(until=until)` (a callable usable in `Depends()`; the instance only carries the *declared* `until` and is never mutated). `VersionInfo` is a `NamedTuple(origin, until)`; the middleware stores one per route under the `VERSION_INFO_ATTR` attribute on the `APIRoute` itself. `VersioningSupport.__call__` is `async`, takes `request: Request`, and resolves the info via `request.scope["route"]` (set by FastAPI since 0.95); it raises a diagnostic `RuntimeError` ("Versioning is not initialized…") when the route was never processed. Endpoints inject `Annotated[VersionInfo, Depends(versioning())]`. NOTE: this file deliberately has NO `from __future__ import annotations` (FA100 is per-file-ignored): FastAPI can't resolve postponed annotations of a callable-instance dependency because the instance has no `__globals__` — use `X | None` syntax (not string-quoted types).
- `src/fastapi_easy_versioning/middleware.py` — the real logic.

Middleware mechanics (in `middleware.py`):
- **Plain ASGI middleware** (no `BaseHTTPMiddleware`): `__init__(self, app, *, rebuild_openapi: bool = True)`, and `__call__` runs the build once, then always delegates to `self.app`.
- **Build-once**: the build runs on the first ASGI event whose `scope["app"]` is a `Starlette` (guarded by a `self._built` flag) — under a real server (uvicorn) that is the **lifespan startup** event for a root-mounted middleware, but the **first HTTP request** in the httpx test suite (ASGITransport skips lifespan) or when the middleware sits on a *mounted* sub-app (mounts don't receive lifespan). Routes/versions added later require an explicit `rebuild_versioning(app)` call — the public function the middleware itself delegates to (idempotent; it also re-resolves default `until` against a new max version).
- **Version discovery** (`_build_version_mapping`): a sub-app counts as a version only if it is a starlette `Mount`, `.app` is a `FastAPI`, and `.app.extra["api_version"]` is an `int` **and not a `bool`** (`API_VERSION_KEY = "api_version"`; version `0` is valid). Pass it as `FastAPI(api_version=N)` — unknown kwargs land in `.extra`. A present-but-non-int `api_version` emits a `UserWarning`. Mapping is sorted ascending. An empty mapping is a graceful no-op.
- **Opt-in**: a route is "managed" only if it has a dependency whose `.call` is a `VersioningSupport`; others are skipped and stay only in their own sub-app. Only `APIRoute` (HTTP) — WebSocket routes are not inherited.
- **`until` resolution**: `min` of all declared `until` values on the route's deps, capped by `max(mapping)`; defaults to `max(mapping)` when none declared. So `versioning()` with no `until` means "available through the latest version". `until` below the declaring version emits a `UserWarning` (the route is then inherited nowhere).
- **Inheritance** (`_inherit_route`): each target version in `range(origin+1, until+1)` gets a **shallow `copy.copy` of the route** with `dependency_overrides_provider` rebound to the target app and the handler rebuilt via `request_response(inherited.get_route_handler())` — `request_response` MUST be imported from `fastapi.routing` (newer FastAPI ships its own copy wiring the dependencies' AsyncExitStack into scope; starlette's breaks). Inheritance into a version that already defines the same path+methods is skipped (`_has_route`) — redefinition shadows both at runtime and in OpenAPI.
- **OpenAPI**: after copying, `openapi_schema = None` then `app.openapi()` per version (the reset matters — `FastAPI.openapi()` caches), unless `rebuild_openapi=False`.

`VersioningMiddleware.__init__(self, app, *, rebuild_openapi: bool = True)` — `app` is supplied by `add_middleware`/`Middleware`, so you only pass `rebuild_openapi` as a keyword. When `False`, routes are still inherited at runtime but inherited endpoints do NOT appear in each version's `/docs`.

## Commands

Toolchain is 100% `uv` (build backend is `uv_build`, no Makefile/tox/nox). `uv.lock` is committed; CI uses `--frozen`. A `Justfile` wraps the common dev commands:

```bash
just init   # uv sync — create venv + install all dev deps
just test   # uv run -m pytest (coverage forced via addopts)
just lint   # ruff check + ruff format --check + ty check src
just fmt    # uv run ruff format
just hooks  # uv run pre-commit run --all-files
just docs   # uv run mkdocs serve
just build  # uv build (sdist + wheel)
```

Raw `uv` equivalents (used directly in CI):

```bash
uv sync --group=test --frozen        # what CI does for tests
uv run -m pytest                     # run tests
uv run -m coverage lcov              # CI coverage step
uv run ruff check                    # lint
uv run ty check src                  # typecheck
uv version --bump patch              # bump version (patch|minor|major)
```

Run examples locally:
```bash
uvx --python=3.14 --from="fastapi[standard]" --with="fastapi-easy-versioning" \
  fastapi dev examples/simple_versioning.py
```

## Conventions & gotchas

- **Commits**: Conventional Commits. Do NOT add a `Co-Authored-By: Claude` trailer.
- **Release flow**: bumping the version in `pyproject.toml` (static `version = "..."`) + committing does NOT publish. PyPI publish (`release.yml`) fires ONLY when a GitHub Release is `published`, via `uv build && uv publish` over OIDC trusted publishing (no token secret). Version bumps are dedicated `chore: bump to X` commits.
- **CI**: lint (`ruff check` + `ty check src`) and tests (matrix 3.10–3.14) run on PR/push to master, ignoring `docs/**`, `README.md`, `LICENSE`. Docs auto-deploy to GitHub Pages on EVERY push to master.
- **Dependabot** (`.github/dependabot.yml`): one grouped weekly PR bumping ONLY dev dependencies. `dependency-type: development` scopes updates to the PEP 735 `[dependency-groups]`; `[project.dependencies]` (fastapi) are classified production and deliberately excluded so their intentional lower bounds stay put. It won't touch pre-commit hook revs — bump those with `pre-commit autoupdate`.
- **pre-commit**: hooks include ruff-check, ruff-format, `uv-lock`, `ty`. Hook revs are kept in sync with the `pyproject` dev pins via `pre-commit autoupdate` (e.g. ruff `v0.15.20` ↔ `ruff~=0.15.20`). `ruff format --check` is enforced ONLY via pre-commit, not CI.
- **Type checker is `ty`** (Astral, preview — pinned `ty~=0.0.56`), NOT mypy. There is no `strict = true` analog; ty uses its default rule set and `[tool.ty.terminal] error-on-warning` defaults to `true` (warnings fail too). `[tool.ty.environment] python-version = "3.10"`. `tests` are excluded via `[tool.ty.src] exclude`. ty resolves third-party imports (fastapi) straight from `pyproject.toml` — the pre-commit hook takes NO `additional_dependencies` (unlike the old mypy hook), and checks the whole project (minus `tests`), while CI narrows to `ty check src`.
- **`api_version` must be an `int` (not `bool`)** — a `str`/`float`/`bool` value warns and is ignored; an unmounted sub-app is silently ignored. Version `0` is valid.
- **`versioning()` (until=None)** means "available through the latest version", NOT "only this version" — a common surprise.
- **Endpoints without `Depends(versioning())` are never inherited** and are invisible to the system; opting in is mandatory.
- **Nothing is versioned until the first ASGI event** reaches the middleware (build-once — lifespan startup under a real server, first request in the test suite); route copying mutates the sub-apps' `router.routes` at runtime, not at import/decoration time. Anything added after that needs an explicit `rebuild_versioning(app)`.
- **Ruff is maximal**: `lint.select = ['ALL']` with `preview = true` (docstring `D*` rules and a few others are the main opt-outs; per-file relaxations for `examples/*` and `tests/*`). Expect new code to trip many rules, and note `fix = true` auto-applies safe fixes on `ruff check`.
- **Tests** import via the src-layout path `src.fastapi_easy_versioning`, so run from repo root. Async via `anyio` — each test file needs module-level `pytestmark = [pytest.mark.anyio]` plus the session-scoped `anyio_backend` fixture (`"asyncio"`). Shared fixtures (`app`, `client`, `middleware_setup`, `v1`, `v2`) are in `tests/conftest.py`.
- **Docs are bilingual (RU + EN)** built with mkdocs-material + `mkdocs-static-i18n`. `docs/ru/*` is the source of truth; `docs/en/*` is marked auto-translated. Mirror the same 5 pages (index, dependency, middleware, examples/simple, examples/multiple) in both, and update BOTH `nav:` lists in `mkdocs.yml` when adding a page.
- **Drift risk**: the quick-start example is copied near-verbatim across `README.md`, `docs/en/index.md`, `docs/ru/index.md`; the `docs/*/examples/*.md` code blocks are near-verbatim copies of `examples/*.py` (docs omit the in-file `# To run…` comment and use a clone-prefixed run command). Any public-API change must be propagated to all copies.
