# Multiple APIs Versioning Example

!!! warning "The English documentation has been automatically translated. If you notice any grammatical or semantic errors, please help improve it by contributing corrections on [GitHub](https://github.com/feodor-ra/fastapi-easy-versioning), or refer to the original Russian documentation."

The example is available on [GitHub](https://github.com/feodor-ra/fastapi-easy-versioning/blob/master/examples/multiple_versioning.py).

To run it locally, clone the repository and execute the following command:

```bash
git clone https://github.com/feodor-ra/fastapi-easy-versioning.git
```

```bash
uvx --python=3.13 --from="fastapi[standard]" --with="fastapi-easy-versioning" fastapi dev fastapi-easy-versioning/examples/multiple_versioning.py
```

The example contains the following code:

```python
from fastapi import Depends, FastAPI, middleware
from fastapi_easy_versioning import (
    VersioningMiddleware,
    versioning,
)

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


@private_v1.get("/endpoint", dependencies=[Depends(versioning(until=1))])
def private_endpoint() -> str:
    return "I'm v1 private endpoint"


@private_v1.get("/another-endpoint", dependencies=[Depends(versioning())])
def private_another_endpoint() -> str:
    return "I'm v1 private another endpoint"


@private_v2.get("/endpoint", dependencies=[Depends(versioning())])
def private_endpoint_v2() -> str:
    return "I'm v2 private endpoint"


@public_v1.get("/endpoint", dependencies=[Depends(versioning(until=1))])
def public_endpoint() -> str:
    return "I'm v1 public endpoint"


@public_v1.get("/another-endpoint", dependencies=[Depends(versioning())])
def public_another_endpoint() -> str:
    return "I'm v1 public another endpoint"


@public_v2.get("/endpoint", dependencies=[Depends(versioning())])
def public_endpoint_v2() -> str:
    return "I'm v2 public endpoint"
```

This code creates two independent versioned APIs: public and private. Each has two versions (v1 and v2). Swagger documentation for them is available at:

- Public API v1: <http://127.0.0.1:8000/api/public/v1/docs>
- Public API v2: <http://127.0.0.1:8000/api/public/v2/docs>
- Private API v1: <http://127.0.0.1:8000/api/private/v1/docs>
- Private API v2: <http://127.0.0.1:8000/api/private/v2/docs>

The resulting structure is as follows:

- In the public API:
  - `/endpoint` is available only in version v1 (with `until=1` restriction)
  - `/another-endpoint` is available in all versions (starting from v1)
  - in v2, a new `/endpoint` is added, which overrides the version from v1

- In the private API:
  - `/endpoint` is available only in version v1 (with `until=1` restriction)
  - `/another-endpoint` is available in all versions (starting from v1)
  - in v2, a new `/endpoint` is added, which overrides the version from v1

Both APIs operate independently thanks to the use of separate `VersioningMiddleware` instances.

```mermaid
graph TD
    A[Endpoint Availability] --> B[Public API]
    A --> C[Private API]

    B --> B1[v1<br/>api_version=1]
    B --> B2[v2<br/>api_version=2]

    C --> C1[v1<br/>api_version=1]
    C --> C2[v2<br/>api_version=2]

    B1 --> B11["/endpoint ✓<br/>(until=1)"]
    B1 --> B12["/another-endpoint ✓"]

    B2 --> B21["/endpoint ✓<br/>(from v2)"]
    B2 --> B22["/another-endpoint ✓"]

    C1 --> C11["/endpoint ✓<br/>(until=1)"]
    C1 --> C12["/another-endpoint ✓"]

    C2 --> C21["/endpoint ✓<br/>(from v2)"]
    C2 --> C22["/another-endpoint ✓"]

    style B11 fill:#90EE90
    style B12 fill:#90EE90
    style B21 fill:#90EE90
    style B22 fill:#90EE90

    style C11 fill:#90EE90
    style C12 fill:#90EE90
    style C21 fill:#90EE90
    style C22 fill:#90EE90

    classDef available fill:#90EE90,stroke:#333;
    classDef notAvailable fill:#FFB6C1,stroke:#333;
```
