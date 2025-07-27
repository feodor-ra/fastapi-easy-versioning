# FastAPI Easy Versioning

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/fastapi-easy-versioning)
![PyPI - Downloads](https://img.shields.io/pypi/dm/fastapi-easy-versioning)
![GitHub Release](https://img.shields.io/github/v/release/feodor-ra/fastapi-easy-versionings)
![GitHub Repo stars](https://img.shields.io/github/stars/feodor-ra/fastapi-easy-versioning?style=flat)
![Test results](https://github.com/feodor-ra/fastapi-easy-versioning/actions/workflows/tests.yml/badge.svg)
[![Coverage Status](https://coveralls.io/repos/github/feodor-ra/fastapi-easy-versioning/badge.svg?branch=master)](https://coveralls.io/github/feodor-ra/fastapi-easy-versioning?branch=master)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://feodor-ra.github.io/fastapi-easy-versioning/)

This is a solution for building versioned APIs automatically using [FastAPI](https://fastapi.tiangolo.com). It enables automatic inheritance of endpoints from previous FastAPI sub-applications into newer versions based on configuration, and correctly reflects them in the OpenAPI schema.

[Documentation](https://feodor-ra.github.io/fastapi-easy-versioning/)

## Installation

```bash
pip install fastapi-easy-versioning
```

[PyPI](https://pypi.org/project/fastapi-easy-versioning/)

## Usage

To implement versioning, use the `VersioningMiddleware` and the dependency factory `versioning`.

Example:

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

The endpoint `/only-v1` is available only in version `v1` at `/v1/only-v1`.
The endpoint `/from-v2` becomes available starting from version `v2` at `/v2/from-v2` and is automatically inherited in all subsequent versions.
The endpoint `/all-versions`, defined in `v1`, is accessible at both `/v1/all-versions` and `/v2/all-versions` due to the inheritance mechanism.

Using the `versioning` dependency factory, you can specify the last version in which an endpoint remains available by setting the `until` parameter to a version number. If `until` is set to `None` or omitted, the endpoint will be available in the version it was declared and in all later versions.

To associate a sub-application with a specific version, use the `api_version` parameter when creating the `FastAPI` instance. It must be an integer. Sub-applications without the `api_version` parameter will be ignored during versioning processing.

---

[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/feodor-ra/fastapi-easy-versioning/blob/master/.pre-commit-config.yaml)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/feodor-ra/fastapi-easy-versioning/releases)

![GitHub License](https://img.shields.io/github/license/feodor-ra/fastapi-easy-versioning)
