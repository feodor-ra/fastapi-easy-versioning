# fastapi-easy-versioning

[English](https://github.com/feodor-ra/fastapi-easy-versioning/blob/master/README.md) · **Русский**

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
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue)](https://feodor-ra.github.io/fastapi-easy-versioning/ru/)

**Версионированные API на FastAPI** — одно субприложение на версию, автоматическое наследование эндпоинтов из старых версий в новые и своя актуальная OpenAPI-схема у каждой версии.

Когда API живёт в нескольких версиях, между ними приходится вручную копировать роуты: `/v2` должен отдавать всё, что отдавал `/v1`, кроме того, что осознанно выпилили. Копии расползаются, `/v1/docs` и `/v2/docs` начинают врать, а «в какой версии этот эндпоинт вообще есть» становится вопросом к `git blame`. Этот пакет делает диапазон доступности **свойством эндпоинта**: объявляете его один раз, помечаете зависимостью — и он сам оказывается во всех последующих версиях.

```python
app = FastAPI()
app.add_middleware(VersioningMiddleware)
app.mount("/v1", app_v1)
app.mount("/v2", app_v2)


@app_v1.get("/items", dependencies=[Depends(versioning())])
def items() -> list[Item]:
    return get_items()
```

Объявлен один раз в v1 — обслуживается и по `/v1/items`, и по `/v2/items`, и присутствует в Swagger обеих версий. Без дублирования роута и без схемы, поддерживаемой руками.

## Установка

```bash
pip install fastapi-easy-versioning
```

Требуется Python **3.10+** и FastAPI **≥ 0.95** (версии `0.137.0` и `0.137.1` исключены). `fastapi` — единственная рантайм-зависимость.

## Как это использовать

Версионирование строится из двух частей, которые работают **только вместе**.

**1. Смонтируйте по субприложению на версию и добавьте middleware.** Middleware добавляется в агрегирующее приложение — то, которое непосредственно монтирует версии, — но не в сами версии.

```python
from fastapi import Depends, FastAPI
from fastapi_easy_versioning import VersioningMiddleware, versioning

app = FastAPI()
app_v1 = FastAPI(api_version=1)  # номер версии — целое число; 0 допустим
app_v2 = FastAPI(api_version=2)

app.mount("/v1", app_v1)
app.mount("/v2", app_v2)
app.add_middleware(VersioningMiddleware)
```

**2. Пометьте эндпоинты.** Пометка обязательна: эндпоинт без зависимости остаётся только в своей версии.

```python
@app_v1.get("/only-v1", dependencies=[Depends(versioning(until=1))])
def only_v1() -> str:
    return "Я доступен только в версии v1"


@app_v1.get("/all-versions", dependencies=[Depends(versioning())])
def all_versions() -> str:
    return "Я доступен во всех версиях, начиная с v1"


@app_v2.get("/from-v2", dependencies=[Depends(versioning())])
def from_v2() -> str:
    return "Я доступен начиная с версии v2 и во всех последующих"
```

`versioning()` без `until` означает «до последней версии», а не «только в этой» — частый источник недоразумений. Зависимость принимается везде, где её принимает FastAPI, в том числе в `APIRouter(dependencies=[...])`, чтобы разом версионировать весь роутер.

**3. Читайте метаданные версии там, где нужно.** Внедрённая в сигнатуру, та же зависимость возвращает разрешённый диапазон:

```python
@app_v1.get("/where-am-i")
def where_am_i(version: Annotated[VersionInfo, Depends(versioning())]) -> str:
    return f"Доступен с v{version.origin} по v{version.until}"
```

В результате: `/v1/only-v1` отвечает, а `/v2/only-v1` возвращает 404; `/all-versions` отвечает в обеих версиях; `/v2/from-v2` отвечает, а `/v1/from-v2` возвращает 404 — и `/docs` каждой версии показывает ровно то, что эта версия обслуживает.

## Почему это круто

- **Объявил один раз — наследуется дальше**: эндпоинт из v1 обслуживается всеми последующими версиями, и каждая получает собственную копию роута.
- **Точный диапазон доступности**: `until` задаёт последнюю версию, в которой живёт эндпоинт; из нескольких пометок на роуте действует минимальная.
- **Переопределение затеняет**: свой эндпоинт на том же пути в новой версии заменяет унаследованный — и в рантайме, и в OpenAPI.
- **Честная документация версии**: после наследования OpenAPI-схема каждой версии перестраивается, поэтому Swagger не расходится с тем, что реально обслуживается.
- **HTTP и WebSocket**: `APIRoute` и `APIWebSocketRoute` версионируются с одинаковой семантикой, а затенение учитывает вид роута.
- **Несколько независимых API**: public и private API в одном приложении версионируются раздельно — по одному middleware на каждое агрегирующее приложение.
- **Ничего, кроме FastAPI**: единственная рантайм-зависимость, полная типизация (`py.typed`), тесты против FastAPI от 0.95 до новейшей на Python 3.10–3.14.

## Документация

📖 **[Полная документация](https://feodor-ra.github.io/fastapi-easy-versioning/ru/)** — быстрый старт, руководство (зависимость, middleware, рецепты, ограничения), запускаемые примеры и авто-генерируемый справочник API. Доступна на русском и английском.

## Лицензия

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
