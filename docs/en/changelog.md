---
title: Changelog
---

# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] — 2026-07-29

No functional changes: the library behaves exactly as in 0.4.0.

### Changed

- The docstrings of the public API were substantially expanded — they now spell
  out the `until` resolution rules, the build-once behaviour and the diagnostics,
  and they are what your IDE shows on hover. The same docstrings back the new
  auto-generated [API reference](reference/dependency.md).
- Package metadata: `keywords` filled in, `Homepage` repointed from the
  repository to the documentation site, and `Issues` / `Changelog` URLs added.
- The build backend requirement was widened to `uv_build>=0.8.3,<0.12.0`.

## [0.4.0] — 2026-07-07

### Added

- WebSocket routes are versioned on par with HTTP ones: `APIWebSocketRoute` is
  inherited between versions with the same `until` semantics, and shadowing is
  kind-aware — an HTTP route and a WebSocket on the same path never conflict.
- `api_version` and `until` are validated. A non-`int` (or `bool`) `api_version`
  and an `until` below the declaring version now emit a `UserWarning` instead of
  failing silently.
- `API_VERSION_KEY` is exported from the package root.

### Changed

- **Breaking.** The middleware was rewritten as plain ASGI middleware (no
  `BaseHTTPMiddleware`) and builds the inheritance exactly once — on the first
  ASGI event. Routes or versions added after that need an explicit
  `rebuild_versioning(app)`, which is now public.
- **Breaking.** Every inheriting version receives its own copy of the route, with
  `dependency_overrides` bound to the target application, instead of sharing a
  single route object between versions.
- **Breaking.** Version metadata is stored per route in a registry on the version
  sub-application, rather than by mutating the shared dependency instance. A
  router included into several versions now resolves correctly.
- Python 3.9 support dropped; the supported range is 3.10–3.14.

### Fixed

- FastAPI 0.137+ is supported: routes are walked through the public
  `iter_route_contexts` iterator of the new router tree, so endpoints added with
  `include_router` are versioned together with their include-time prefixes and
  dependencies. FastAPI `0.137.0` and `0.137.1` are excluded at the dependency
  level — the tree landed there but the public iterator only in `0.137.2`.
- Version `0` is treated as a valid version (explicit `None` checks instead of
  truthiness).
- An application that mounts no versioned sub-app is a graceful no-op instead of
  raising.

## [0.3.0] — 2026-07-07

### Added

- Python 3.14 support.

## [0.2.0] — 2025-10-16

### Added

- The `rebuild_openapi` flag on `VersioningMiddleware`. With `False` the
  endpoints are still inherited and served, but inherited ones do not appear in
  the version's OpenAPI schema and `/docs`.

## [0.1.0] — 2025-07-27

### Added

- First release: `VersioningMiddleware` and the `versioning()` dependency —
  one FastAPI sub-application per version, inheritance of marked endpoints from
  older versions into newer ones, and a regenerated OpenAPI schema per version.

[0.4.1]: https://github.com/feodor-ra/fastapi-easy-versioning/releases/tag/v0.4.1
[0.4.0]: https://github.com/feodor-ra/fastapi-easy-versioning/releases/tag/v0.4.0
[0.3.0]: https://github.com/feodor-ra/fastapi-easy-versioning/releases/tag/v0.3.0
[0.2.0]: https://github.com/feodor-ra/fastapi-easy-versioning/releases/tag/v0.2.0
[0.1.0]: https://github.com/feodor-ra/fastapi-easy-versioning/releases/tag/v0.1.0
