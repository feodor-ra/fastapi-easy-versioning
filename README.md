# fastapi-easy-versioning

**English** · [Русский](https://github.com/feodor-ra/fastapi-easy-versioning/blob/master/README.ru.md)

[![PyPI - Version](https://img.shields.io/pypi/v/fastapi-easy-versioning)](https://pypi.org/project/fastapi-easy-versioning/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/fastapi-easy-versioning)
![PyPI - Status](https://img.shields.io/pypi/status/fastapi-easy-versioning)
![PyPI - Downloads](https://img.shields.io/pypi/dm/fastapi-easy-versioning)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

![GitHub Release](https://img.shields.io/github/v/release/feodor-ra/fastapi-easy-versioning)
![GitHub Repo stars](https://img.shields.io/github/stars/feodor-ra/fastapi-easy-versioning?style=flat)
![GitHub last commit](https://img.shields.io/github/last-commit/feodor-ra/fastapi-easy-versioning)
[![Tests](https://github.com/feodor-ra/fastapi-easy-versioning/actions/workflows/tests.yml/badge.svg)](https://github.com/feodor-ra/fastapi-easy-versioning/actions/workflows/tests.yml)
[![Coverage Status](https://coveralls.io/repos/github/feodor-ra/fastapi-easy-versioning/badge.svg?branch=master)](https://coveralls.io/github/feodor-ra/fastapi-easy-versioning?branch=master)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue)](https://feodor-ra.github.io/fastapi-easy-versioning/)

**Versioned APIs for FastAPI** — one sub-application per version, automatic inheritance of endpoints from older versions into newer ones, and an up-to-date OpenAPI schema for every version.

Once an API lives in several versions, routes have to be copied between them by hand: `/v2` must serve everything `/v1` served, minus what was deliberately dropped. The copies drift apart, `/v1/docs` and `/v2/docs` start lying, and "which versions is this endpoint even in?" becomes a question for `git blame`. This package makes the availability range a **property of the endpoint**: declare it once, mark it with a dependency, and it shows up in every later version by itself.

```python
app = FastAPI()
app.add_middleware(VersioningMiddleware)
app.mount("/v1", app_v1)
app.mount("/v2", app_v2)


@app_v1.get("/items", dependencies=[Depends(versioning())])
def items() -> list[Item]:
    return get_items()
```

Declared once in v1 — served at `/v1/items` **and** `/v2/items`, and present in both versions' Swagger. No duplicated route, no hand-maintained schema.

## Install

```bash
pip install fastapi-easy-versioning
```

Requires Python **3.10+** and FastAPI **≥ 0.95** (`0.137.0` and `0.137.1` are excluded). `fastapi` is the only runtime dependency.

## How to use it

Versioning is built from two pieces that work **only together**.

**1. Mount one sub-application per version and add the middleware.** The middleware goes on the aggregating application — the one that directly mounts the versions, never on the versions themselves.

```python
from fastapi import Depends, FastAPI
from fastapi_easy_versioning import VersioningMiddleware, versioning

app = FastAPI()
app_v1 = FastAPI(api_version=1)  # the version number is an int; 0 is valid
app_v2 = FastAPI(api_version=2)

app.mount("/v1", app_v1)
app.mount("/v2", app_v2)
app.add_middleware(VersioningMiddleware)
```

**2. Mark the endpoints.** Marking is opt-in: an endpoint without the dependency stays in its own version only.

```python
@app_v1.get("/only-v1", dependencies=[Depends(versioning(until=1))])
def only_v1() -> str:
    return "Available only in version v1"


@app_v1.get("/all-versions", dependencies=[Depends(versioning())])
def all_versions() -> str:
    return "Available in all versions starting from v1"


@app_v2.get("/from-v2", dependencies=[Depends(versioning())])
def from_v2() -> str:
    return "Available starting from v2 and in all future versions"
```

`versioning()` without `until` means "through the latest version", not "in this one only" — a common source of surprise. The dependency is accepted anywhere FastAPI accepts one, including `APIRouter(dependencies=[...])` to version a whole router at once.

**3. Read the version metadata where you need it.** Injected into the signature, the same dependency yields the resolved range:

```python
@app_v1.get("/where-am-i")
def where_am_i(version: Annotated[VersionInfo, Depends(versioning())]) -> str:
    return f"Available from v{version.origin} through v{version.until}"
```

The result: `/v1/only-v1` responds while `/v2/only-v1` is a 404; `/all-versions` responds in both; `/v2/from-v2` responds while `/v1/from-v2` is a 404 — and each version's `/docs` shows exactly what that version serves.

## Why it's cool

- **Declare once, inherit forward** — an endpoint declared in v1 is served by every later version, each with its own copy of the route.
- **An exact availability range** — `until` caps the last version an endpoint lives in; several markers on one route resolve to the smallest.
- **Redefinition shadows** — an endpoint of your own on the same path in a newer version replaces the inherited one, at runtime and in OpenAPI alike.
- **Honest per-version docs** — every version's OpenAPI schema is regenerated after inheritance, so Swagger never drifts from what is actually served.
- **HTTP and WebSocket** — `APIRoute` and `APIWebSocketRoute` are versioned with identical semantics, and shadowing is kind-aware.
- **Several independent APIs** — public and private APIs in one application version separately, one middleware per aggregating app.
- **Nothing but FastAPI** — a single runtime dependency, fully typed (`py.typed`), tested against FastAPI 0.95 through the latest on Python 3.10–3.14.

## Documentation

📖 **[Full documentation](https://feodor-ra.github.io/fastapi-easy-versioning/)** — quickstart, the guide (dependency, middleware, recipes, limitations), runnable examples and an auto-generated API reference. Available in English and Russian.

## License

[MIT](https://github.com/feodor-ra/fastapi-easy-versioning/blob/master/LICENSE).

---

[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/feodor-ra/fastapi-easy-versioning/blob/master/.pre-commit-config.yaml)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![pytest](https://img.shields.io/badge/tested_with-pytest-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Material for MkDocs](https://img.shields.io/badge/Material_for_MkDocs-526CFE?logo=materialformkdocs&logoColor=white)](https://squidfunk.github.io/mkdocs-material/)
[![Conventional Commits](https://img.shields.io/badge/Conventional_Commits-1.0.0-FE5196?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/feodor-ra/fastapi-easy-versioning/releases)

![GitHub License](https://img.shields.io/github/license/feodor-ra/fastapi-easy-versioning)
