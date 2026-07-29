---
title: Рецепты
---

# Рецепты

Готовые приёмы для типовых задач.

## Версионировать целый роутер

Зависимость, повешенная на `APIRouter`, распространяется на все его эндпоинты — помечать каждый по отдельности не нужно.

```python
from fastapi import APIRouter, Depends, FastAPI
from fastapi_easy_versioning import versioning

users = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(versioning())])


@users.get("")
def list_users() -> list[User]: ...


@users.get("/{user_id}")
def get_user(user_id: int) -> User: ...


app_v1.include_router(users)
```

Один и тот же роутер можно включить в несколько версий — версией объявления для каждого набора роутов станет то приложение, в которое он включён.

!!! tip "Ограничить весь роутер"

    `APIRouter(dependencies=[Depends(versioning(until=2))])` ограничивает разом все эндпоинты роутера. Если на конкретном эндпоинте указан свой `until`, сработает [минимальный из двух](dependency.md#until).

## Исключить эндпоинт из версионирования

Обратная задача решается отсутствием пометки: служебные и внутренние ручки просто не получают `versioning()`.

```python
@app_v1.get("/healthz")  # (1)!
def healthz() -> str:
    return "ok"
```

1. Останется только в v1. Ни в одну другую версию не попадёт и в их схемах не появится.

## Заменить эндпоинт в новой версии

Достаточно объявить в новой версии свой эндпоинт с тем же путём: наследование в неё пропускается, а старая реализация продолжает работать в старых версиях.

```python
@app_v1.get("/profile", dependencies=[Depends(versioning())])
def profile_v1() -> ProfileV1: ...


@app_v3.get("/profile", dependencies=[Depends(versioning())])  # (1)!
def profile_v3() -> ProfileV3: ...
```

1. v1 и v2 отдают старый формат, v3 и все последующие — новый. В `/v3/docs` попадёт только новая схема ответа.

## Добавить версию во время работы приложения

Наследование строится один раз, поэтому смонтированная позже версия требует явной пересборки.

```python
from fastapi_easy_versioning import rebuild_versioning

app_v3 = FastAPI(api_version=3)
app.mount("/v3", app_v3)

rebuild_versioning(app)  # (1)!
```

1. Вызов идемпотентен: он не создаёт дублей для уже унаследованных роутов, зато пересчитывает `until` по умолчанию — теперь «до последней версии» означает v3.

То же самое нужно после `include_router` или `add_api_route` на уже работающем приложении. Подробнее — в [разделе про рантайм](middleware.md#runtime).

## Два независимых API в одном приложении

Каждое агрегирующее приложение получает свой middleware — и свою независимую нумерацию версий.

```python
app = FastAPI()

public_app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware)])
private_app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware)])

app.mount("/api/public", public_app)
app.mount("/api/private", private_app)

public_app.mount("/v1", FastAPI(api_version=1))
private_app.mount("/v1", FastAPI(api_version=1))
```

Полный разбор — в [примере](../examples/multiple.md).

## Версионировать WebSocket { #websocket }

WebSocket-роуты версионируются наравне с HTTP — с той же семантикой `until` и тем же затенением. Различается только способ пометки:

=== "fastapi ≥ 0.100"

    ```python
    @app_v1.websocket("/ws", dependencies=[Depends(versioning())])
    async def ws(websocket: WebSocket) -> None: ...
    ```

=== "fastapi 0.95"

    ```python
    @app_v1.websocket("/ws")  # (1)!
    async def ws(
        websocket: WebSocket,
        version: Annotated[VersionInfo, Depends(versioning())],
    ) -> None: ...
    ```

    1. Параметра `dependencies` у `websocket()` в 0.95 ещё нет — пометка ставится зависимостью в сигнатуре.

## Скрыть унаследованные эндпоинты из Swagger

Если унаследованные роуты должны обслуживаться, но не показываться в `/docs` новых версий, отключите пересборку схемы:

```python
app.add_middleware(VersioningMiddleware, rebuild_openapi=False)
```

Каждая версия сохранит ту схему, которую FastAPI собрал по её собственным роутам.

## Отдавать номер версии клиенту

`VersionInfo` доступен в эндпоинте как обычная зависимость — например, чтобы положить границы поддержки в заголовок ответа:

```python
@app_v1.get("/items", dependencies=[Depends(versioning())])
def items(version: Annotated[VersionInfo, Depends(versioning())]) -> Response:
    return JSONResponse(
        get_items(),
        headers={"X-API-Deprecated-After": str(version.until)},
    )
```
