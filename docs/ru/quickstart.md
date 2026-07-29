---
title: Быстрый старт
---

# Быстрый старт

За несколько минут: смонтировать версии, включить middleware, пометить эндпоинты и увидеть результат в Swagger.

Версионирование строится из двух частей, которые работают **только вместе**:

- [`VersioningMiddleware`](guide/middleware.md) — добавляется в приложение, монтирующее версии;
- [`versioning()`](guide/dependency.md) — зависимость, помечающая эндпоинт как версионированный.

## 1. Создайте приложения-версии

Версия — обычное FastAPI-приложение с extra-параметром `api_version`. Значение должно быть целым числом; `0` допустим.

```python
from fastapi import FastAPI

app = FastAPI()
app_v1 = FastAPI(api_version=1)  # (1)!
app_v2 = FastAPI(api_version=2)

app.mount("/v1", app_v1)  # (2)!
app.mount("/v2", app_v2)
```

1. `api_version` — не стандартный параметр FastAPI: неизвестные ключевые аргументы попадают в `app.extra`, откуда middleware его и читает.
2. Префикс монтирования произвольный — версии различаются по `api_version`, а не по пути.

## 2. Добавьте middleware

Middleware добавляется в **агрегирующее** приложение — то, которое непосредственно монтирует версии. Не в сами версии.

=== "add_middleware"

    ```python
    app.add_middleware(VersioningMiddleware)
    ```

=== "при создании приложения"

    ```python
    from fastapi import middleware

    app = FastAPI(middleware=[middleware.Middleware(VersioningMiddleware)])
    ```

!!! warning "Только на агрегирующем приложении"

    Добавленный в само `app_v1` middleware не найдёт ни одной версии: он ищет версии среди тех приложений, которые смонтированы непосредственно под ним.

## 3. Пометьте эндпоинты

Версионирование — **opt-in**. Эндпоинт без зависимости `versioning()` остаётся только в своей версии и в наследовании не участвует вовсе.

```python
from fastapi import Depends


@app_v1.get("/only-v1", dependencies=[Depends(versioning(until=1))])
def only_v1() -> str:
    return "Я доступен только в версии v1"


@app_v1.get("/all-versions", dependencies=[Depends(versioning())])  # (1)!
def all_versions() -> str:
    return "Я доступен во всех версиях, начиная с v1"


@app_v2.get("/from-v2", dependencies=[Depends(versioning())])
def from_v2() -> str:
    return "Я доступен начиная с версии v2 и во всех последующих"
```

1. `versioning()` без `until` — это «до последней версии», а не «только в этой». Частый источник недоразумений.

## 4. Проверьте результат

```bash
uvicorn main:app
```

| Запрос | Результат |
| --- | --- |
| `GET /v1/only-v1` | 200 — объявлен в v1 |
| `GET /v2/only-v1` | 404 — ограничен `until=1` |
| `GET /v1/all-versions` | 200 — объявлен в v1 |
| `GET /v2/all-versions` | 200 — унаследован в v2 |
| `GET /v1/from-v2` | 404 — эндпоинт появился только в v2 |
| `GET /v2/from-v2` | 200 |

`/v1/docs` и `/v2/docs` показывают ровно тот состав, который версия действительно обслуживает: OpenAPI-схема перестраивается после наследования.

## 5. Прочитайте метаданные версии

Ту же зависимость можно внедрить в сигнатуру — тогда она вернёт `VersionInfo` с разрешёнными границами диапазона:

```python
from typing import Annotated

from fastapi_easy_versioning import VersionInfo


@app_v1.get("/where-am-i")
def where_am_i(version: Annotated[VersionInfo, Depends(versioning())]) -> str:
    return f"Доступен с v{version.origin} по v{version.until}"
```

`until` здесь — уже разрешённое значение: если явного ограничения не было, вернётся номер последней смонтированной версии.

## Что дальше

- [Зависимость `versioning`](guide/dependency.md) — все способы пометки и диагностика ошибок.
- [Middleware](guide/middleware.md) — правила наследования, OpenAPI, добавление роутов в рантайме.
- [Рецепты](guide/recipes.md) — версионирование целого роутера, несколько независимых API, WebSocket.
- [Ограничения](guide/limitations.md) — совместимость с версиями FastAPI и границы применимости.
