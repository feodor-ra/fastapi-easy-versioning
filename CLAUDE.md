# CLAUDE.md

A small FastAPI library (`fastapi-easy-versioning`, PyPI) for building versioned APIs. You mount one FastAPI sub-app per version under the root app; the library automatically inherits endpoints from older versions into newer ones and regenerates each version's OpenAPI schema. Runtime dep is only `fastapi>=0.95.0`; supports Python 3.9–3.13. src-layout, fully typed (ships `py.typed`).

## Architecture / how it works

Public API is exactly three names re-exported from the package root (keep `src/fastapi_easy_versioning/__init__.py` `__all__` in sync with docs): `VersioningMiddleware`, `VersioningSupport`, `versioning`.

Two pieces must be used **together**:
- **`VersioningMiddleware`** — added ONLY to an aggregating app that mounts the version sub-apps, never to the sub-apps themselves. Multiple instances are supported: each attaches to an app that *directly* mounts a version set (see `examples/multiple_versioning.py` — `public_app`/`private_app`, themselves mounted under the root `app`), so independent APIs version separately.
- **`versioning(*, until=None)`** — dependency factory marking an endpoint (or a whole `APIRouter(dependencies=[...])`) as versioned. `until` is keyword-only.

Key files:
- `src/fastapi_easy_versioning/__init__.py` — re-exports the 3 public names.
- `src/fastapi_easy_versioning/dependency.py` — `versioning()` returns a `VersioningSupport(until=until)` (a callable usable in `Depends()`). `VersioningSupport` holds `self.until` and `self.origin` (init `None`). Its `__call__` raises `RuntimeError("VersioningMiddleware not used")` if `origin`/`until` are still `None`, else returns `self` — so an endpoint can inject `Annotated[VersioningSupport, Depends(versioning())]` and read `.origin` / `.until`. (Imports `Self` from `typing_extensions`, an undeclared dep pulled in transitively via fastapi/pydantic.)
- `src/fastapi_easy_versioning/middleware.py` — the real logic.

Middleware mechanics (in `middleware.py`):
- Subclasses starlette `BaseHTTPMiddleware`, but `dispatch()` is a no-op passthrough (`await call_next(request)`). Real work is in the overridden ASGI `__call__`, which calls `_build_versioning_routes(app)` before delegating to `super().__call__`.
- **Lazy + cached**: the overridden `__call__` runs `_build_versioning_routes` on the first ASGI event whose `scope["app"]` is a `Starlette` — under a real server (uvicorn) that is the **lifespan startup** event for a root-mounted middleware, but the **first HTTP request** in the httpx test suite (ASGITransport skips lifespan) or when the middleware sits on a *mounted* sub-app (mounts don't receive lifespan). `_latest_setup_routes` (a `set[str]` of route `unique_id`s) short-circuits rebuilds when the versioned-route set is unchanged.
- **Version discovery** (`_build_version_mapping`): a sub-app counts as a version only if it is a starlette `Mount`, `.app` is a `FastAPI`, and `.app.extra["api_version"]` is an `int` (`API_VERSION_KEY = "api_version"`). Pass it as `FastAPI(api_version=N)` — unknown kwargs land in `.extra`. Mapping is sorted ascending (low version first).
- **Opt-in**: a route is "managed" only if it has a dependency whose `.call` is a `VersioningSupport`; others are skipped and stay only in their own sub-app.
- **`until` resolution**: `min` of all specified `until` values on the route's deps, defaulting to `max(mapping)` (highest declared version) when `None`. So `versioning()` with no `until` means "available through the latest version".
- **`origin`**: set as `dependency.origin or version` while iterating low→high, capturing the declaring version and never overwriting it.
- **Inheritance**: the SAME `APIRoute` object (by reference, not a copy) is appended into every version sub-app in `range(min_version, until+1)`, guarded by `if route not in app.router.routes`. Mutating a route in one version affects all versions that inherited it.
- **OpenAPI**: after copying, `app.openapi_schema = app.openapi()` per version, unless `rebuild_openapi=False`.

`VersioningMiddleware.__init__(self, app, dispatch=None, *, rebuild_openapi: bool = True)` — `app`/`dispatch` are supplied by `add_middleware`/`Middleware`, so you only pass `rebuild_openapi` as a keyword. When `False`, routes are still inherited at runtime but inherited endpoints do NOT appear in each version's `/docs`.

## Commands

Toolchain is 100% `uv` (build backend is `uv_build`, no Makefile/tox/nox). `uv.lock` is committed; CI uses `--frozen`.

```bash
uv sync                              # install (all default deps)
uv sync --group=test --frozen        # what CI does for tests
uv run -m pytest                     # run tests (coverage is forced via addopts)
uv run -m coverage lcov              # CI coverage step
uv run ruff check                    # lint (NOTE: fix=true globally, auto-fixes)
uv run ruff format                   # format (CI does NOT check format; pre-commit does)
uv run mypy src                      # typecheck (CI checks src only; strict=true)
uv run pre-commit run --all-files    # run all hooks
uv build                             # build sdist+wheel
uv run mkdocs serve                  # docs preview
uv version --bump patch              # bump version (patch|minor|major)
```

Run examples locally:
```bash
uvx --python=3.13 --from="fastapi[standard]" --with="fastapi-easy-versioning" \
  fastapi dev examples/simple_versioning.py
```

## Conventions & gotchas

- **Commits**: Conventional Commits. Do NOT add a `Co-Authored-By: Claude` trailer.
- **Release flow**: bumping the version in `pyproject.toml` (static `version = "..."`) + committing does NOT publish. PyPI publish (`release.yml`) fires ONLY when a GitHub Release is `published`, via `uv build && uv publish` over OIDC trusted publishing (no token secret). Version bumps are dedicated `chore: bump to X` commits.
- **CI**: lint (`ruff check` + `mypy src`) and tests (matrix 3.9–3.13) run on PR/push to master, ignoring `docs/**`, `README.md`, `LICENSE`. Docs auto-deploy to GitHub Pages on EVERY push to master.
- **pre-commit**: hooks include ruff-check, ruff-format, `uv-lock`, mypy. Hook pins are slightly ahead of `pyproject` dev pins (ruff `v0.12.12` vs `~=0.12.4`; mypy `v1.17.1` vs `~=1.17.0`) — local pre-commit and `uv run` may use different tool versions. `ruff format --check` is enforced ONLY via pre-commit, not CI.
- **`api_version` must be an `int`** — a `str`/`float` or an unmounted sub-app is silently ignored.
- **`versioning()` (until=None)** means "available through the latest version", NOT "only this version" — a common surprise.
- **Endpoints without `Depends(versioning())` are never inherited** and are invisible to the system; opting in is mandatory.
- **Nothing is versioned until the first ASGI event** reaches the middleware (lazy build — lifespan startup under a real server, first request in the test suite); route copying mutates the sub-apps' `router.routes` at runtime, not at import/decoration time.
- **Ruff is maximal**: `lint.select = ['ALL']` with `preview = true` (docstring `D*` rules and a few others are the main opt-outs; per-file relaxations for `examples/*` and `tests/*`). Expect new code to trip many rules, and note `fix = true` auto-applies safe fixes on `ruff check`.
- **Tests** import via the src-layout path `src.fastapi_easy_versioning`, so run from repo root. Async via `anyio` — each test file needs module-level `pytestmark = [pytest.mark.anyio]` plus the session-scoped `anyio_backend` fixture (`"asyncio"`). Shared fixtures (`app`, `client`, `setup_middleware`, `middleware_setup`) are in `tests/conftest.py`.
- **`tests/test_depenpency.py` is misspelled** (intended `test_dependency.py`); still collected because `python_files = ["test_*.py"]`. Keep or rename deliberately.
- **Docs are bilingual (RU + EN)** built with mkdocs-material + `mkdocs-static-i18n`. `docs/ru/*` is the source of truth; `docs/en/*` is marked auto-translated. Mirror the same 5 pages (index, dependency, middleware, examples/simple, examples/multiple) in both, and update BOTH `nav:` lists in `mkdocs.yml` when adding a page.
- **Drift risk**: the quick-start example is copied near-verbatim across `README.md`, `docs/en/index.md`, `docs/ru/index.md`; the `docs/*/examples/*.md` code blocks are near-verbatim copies of `examples/*.py` (docs omit the in-file `# To run…` comment and use a clone-prefixed run command). Any public-API change must be propagated to all copies.
