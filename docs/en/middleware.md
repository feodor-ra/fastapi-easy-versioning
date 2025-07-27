# Middleware

!!! warning "The English documentation has been automatically translated. If you notice any grammatical or semantic errors, please help improve it by contributing corrections on [GitHub](https://github.com/feodor-ra/fastapi-easy-versioning), or refer to the original Russian documentation."

The `VersioningMiddleware` handles the core functionality of API versioning.

The middleware is added only to the FastAPI application that aggregates sub-applications responsible for specific versions.

```python
from fastapi import FastAPI, Depends
from fastapi_easy_versioning import VersioningMiddleware, versioning

app = FastAPI()
app_v1 = FastAPI(api_version=1)
app_v2 = FastAPI(api_version=2)

app.mount("/v1", app_v1)
app.mount("/v2", app_v2)
app.add_middleware(VersioningMiddleware)
```

If you need to create two or more isolated versioned APIs that should operate independently, you should add `VersioningMiddleware` to each such aggregating application.

```python
from fastapi import Depends, FastAPI, middleware
from fastapi_easy_versioning import VersioningMiddleware

app = FastAPI()

public_app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware)])
public_v1 = FastAPI(api_version=1)
public_v2 = FastAPI(api_version=2)

private_app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware)])
private_v1 = FastAPI(api_version=1)
private_v2 = FastAPI(api_version=2)

app.mount("/api/public", public_app)
public_app.mount("/v1", public_v1)
public_app.mount("/v2", public_v2)

app.mount("/api/private", private_app)
private_app.mount("/v1", private_v1)
private_app.mount("/v2", private_v2)
```

## Versioned Applications Configuration

The middleware identifies which FastAPI applications participate in versioning using the `api_version` extra parameter. If an application doesn't have this parameter, it will be ignored during versioning: endpoints won't be added to it, and endpoints won't be taken from it, even if they were correctly marked with the `VersioningSupport` dependency.

## Middleware Operation

The middleware checks for versioned endpoints and sub-applications on the first request and adds endpoints to sub-applications according to their versioning settings, while also rebuilding the OpenAPI schema.

The middleware caches information about built endpoints and doesn't perform additional work on subsequent requests. However, if a versioned endpoint is added during runtime, it will be added to all relevant sub-applications on the next request, and their OpenAPI schemas will be rebuilt.
