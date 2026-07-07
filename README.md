# FastAPI Easy Versioning

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/fastapi-easy-versioning)
![PyPI - Downloads](https://img.shields.io/pypi/dm/fastapi-easy-versioning)
![GitHub Release](https://img.shields.io/github/v/release/feodor-ra/fastapi-easy-versioning)
![GitHub Repo stars](https://img.shields.io/github/stars/feodor-ra/fastapi-easy-versioning?style=flat)
![Test results](https://github.com/feodor-ra/fastapi-easy-versioning/actions/workflows/tests.yml/badge.svg)
[![Coverage Status](https://coveralls.io/repos/github/feodor-ra/fastapi-easy-versioning/badge.svg?branch=master)](https://coveralls.io/github/feodor-ra/fastapi-easy-versioning?branch=master)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://feodor-ra.github.io/fastapi-easy-versioning/)

A library for building versioned APIs with [FastAPI](https://fastapi.tiangolo.com). Each API version is a separate FastAPI sub-application mounted under a common application. The library automatically inherits endpoints from older versions into newer ones and rebuilds each version's OpenAPI schema, so every version's `/docs` always shows its complete, current set of endpoints.

[Documentation](https://feodor-ra.github.io/fastapi-easy-versioning/)

## Features

- Endpoint inheritance between versions: declare an endpoint once and it is available in all subsequent versions.
- Precise availability range control with the `until` parameter.
- Redefining an endpoint in a newer version shadows the inherited one — both at runtime and in the OpenAPI schema.
- HTTP and WebSocket endpoints are supported.
- Versioning metadata (`origin`, `until`) is readable right inside the endpoint.
- Several independent versioned APIs within one application.
- The only runtime dependency is `fastapi` (versions from 0.95 up to the latest are supported).

## Installation

```bash
pip install fastapi-easy-versioning
```

[PyPI](https://pypi.org/project/fastapi-easy-versioning/)

## Quick Start

Versioning is built from two pieces that only work together:

- `VersioningMiddleware` — added to the application that mounts the versions;
- `versioning()` — a dependency factory that marks an endpoint as versioned.

```python
from fastapi import FastAPI, Depends
from fastapi_easy_versioning import VersioningMiddleware, versioning

app = FastAPI()
app_v1 = FastAPI(api_version=1)
app_v2 = FastAPI(api_version=2)

app.mount("/v1", app_v1)
app.mount("/v2", app_v2)
app.add_middleware(VersioningMiddleware)

@app_v1.get('/only-v1', dependencies=[Depends(versioning(until=1))])
def only_v1() -> str:
    return "Available only in version v1"

@app_v1.get('/all-versions', dependencies=[Depends(versioning())])
def all_versions() -> str:
    return "Available in all versions starting from v1"

@app_v2.get('/from-v2', dependencies=[Depends(versioning())])
def from_v2() -> str:
    return "Available starting from v2 and in all future versions"
```

The result:

- `/v1/only-v1` responds while `/v2/only-v1` returns 404 — the endpoint is limited by `until=1`.
- `/v1/all-versions` and `/v2/all-versions` both respond — the endpoint is declared in `v1` and inherited into `v2`.
- `/v2/from-v2` responds while `/v1/from-v2` returns 404 — the endpoint only appeared in `v2`.
- `/v1/docs` and `/v2/docs` show exactly the endpoints available in the corresponding version.

## How It Works

1. Each version is a `FastAPI(api_version=N)` sub-application mounted under a common application: `app.mount("/v1", app_v1)`. `api_version` must be an integer.
2. On its first ASGI event (server startup or the first request) `VersioningMiddleware` builds the inheritance once: it copies the marked endpoints from older versions into newer ones and rebuilds each version's OpenAPI schema.
3. Only endpoints with the `versioning()` dependency are inherited. An endpoint without it stays only in the version where it is declared.
4. Every inheriting version receives its own copy of the route — changes in one version do not affect the others.

More details — the `versioning` dependency, middleware behavior, adding routes at runtime, FastAPI version compatibility and complete examples — are in the [documentation](https://feodor-ra.github.io/fastapi-easy-versioning/).

---

[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/feodor-ra/fastapi-easy-versioning/blob/master/.pre-commit-config.yaml)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/feodor-ra/fastapi-easy-versioning/releases)

![GitHub License](https://img.shields.io/github/license/feodor-ra/fastapi-easy-versioning)
