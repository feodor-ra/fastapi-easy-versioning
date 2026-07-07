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

Middleware определяет, какие FastAPI-приложения участвуют в версионировании, с помощью extra-параметра `api_version` (константа `API_VERSION_KEY`). Если приложение не имеет этого параметра, оно будет игнорироваться при версионировании: в него не будут добавляться эндпоинты, и из него не будут браться эндпоинты, даже если они были корректно помечены с помощью зависимости `VersioningSupport`. Если `api_version` задан, но не является целым числом (например, `"1"` или `True`), приложение также игнорируется, при этом выдаётся предупреждение `UserWarning`.

## Работа middleware

Middleware строит версионирование один раз — при первом ASGI-событии (под реальным сервером это событие запуска lifespan, при монтировании внутри другого приложения или в тестах — первый запрос). Эндпоинты старых версий копируются в последующие субприложения в соответствии с настройками версионирования, и OpenAPI-схема каждой версии перестраивается. Последующие запросы никакой дополнительной работы не выполняют.

В каждую версию попадает отдельная копия роута:

- изменение роута в одной версии не затрагивает другие версии;
- `dependency_overrides` разрешаются приложением той версии, которая обслуживает запрос;
- если в новой версии объявлен собственный эндпоинт с тем же путём и методами, наследование в неё пропускается — новая версия «перекрывает» старую и в рантайме, и в OpenAPI-схеме.

Версионируются только HTTP-эндпоинты (`APIRoute`) — WebSocket-роуты не наследуются.

Если необходимо отключить перестройку OpenAPI-схемы, можно сделать это при настройке middleware, передав параметр `rebuild_openapi`:

```python
from fastapi import Depends, FastAPI, middleware
from fastapi_easy_versioning import VersioningMiddleware

app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware, rebuild_openapi=False)])

# or

app = FastAPI()
app.add_middleware(VersioningMiddleware, rebuild_openapi=False)
```

## Добавление эндпоинтов во время работы

Версионированный эндпоинт или новая версия, добавленные после первого запроса, автоматически подхвачены не будут. Для этого предназначена публичная функция `rebuild_versioning`: она заново строит наследование и обновляет OpenAPI-схемы версий.

```python
from fastapi_easy_versioning import rebuild_versioning

# после добавления роутов или монтирования новой версии в рантайме
rebuild_versioning(app)  # app — приложение, монтирующее версии
```
