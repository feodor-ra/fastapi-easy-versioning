# Middleware

Основную работу по обеспечению версионирования выполняет middleware `VersioningMiddleware`.

Middleware добавляется только в FastAPI-приложение, которое агрегирует в себе субприложения, отвечающие за конкретные версии.

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

Если требуется создать два или более изолированных версионированных API, каждый из которых должен работать независимо, следует добавить `VersioningMiddleware` в каждое такое агрегирующее приложение.

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

## Настройка приложений-версий

Middleware определяет, какие FastAPI-приложения участвуют в версионировании, с помощью extra-параметра `api_version`. Если приложение не имеет этого параметра, оно будет игнорироваться при версионировании: в него не будут добавляться эндпоинты, и из него не будут браться эндпоинты, даже если они были корректно помечены с помощью зависимости `VersioningSupport`.

## Работа middleware

Middleware проверяет наличие версионированных эндпоинтов и субприложений при первом запросе и добавляет эндпоинты в субприложения в соответствии с их настройками версионирования, а также перестраивает OpenAPI-схему.

Middleware кэширует информацию о построенных эндпоинтах и при последующих запросах не выполняет дополнительную работу. Однако если версионированный эндпоинт будет добавлен во время выполнения приложения, при следующем запросе он будет добавлен во все соответствующие субприложения, и их OpenAPI-схема будет перестроена.
