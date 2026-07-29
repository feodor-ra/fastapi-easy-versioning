# Зависимость для версионирования

Фабрика `versioning()` — способ пометить эндпоинт как версионированный. Она возвращает экземпляр `VersioningSupport`, пригодный для использования в `Depends()`. Эндпоинт без такой зависимости в версионировании не участвует и остаётся только в той версии, где объявлен.

## Семантика `until`

`versioning(*, until: int | None = None)` управляет диапазоном версий, в которых доступен эндпоинт:

| Значение | Поведение |
| --- | --- |
| `until=None` (по умолчанию) | Эндпоинт доступен со своей версии и во всех последующих |
| `until=N` | Эндпоинт доступен со своей версии по версию `N` включительно |

Дополнительные правила:

- Если у роута несколько `versioning`-зависимостей (например, одна на роутере и одна на эндпоинте), действует **минимальный** из указанных `until`.
- `until` меньше версии, в которой объявлен эндпоинт, — противоречие: библиотека выдаст `UserWarning`, эндпоинт останется доступен в своей версии, но не будет унаследован никуда.

## Способы подключения

Зависимость принимается везде, где FastAPI принимает зависимости:

```python
from fastapi import APIRouter, Depends, FastAPI
from fastapi_easy_versioning import versioning

v1_app = FastAPI(api_version=1)

# На эндпоинте — через декоратор
@v1_app.get('/endpoint', dependencies=[Depends(versioning())])
def endpoint() -> None: ...

# Через add_api_route
v1_app.add_api_route('/added', endpoint, dependencies=[Depends(versioning(until=2))])

# Сразу на весь роутер — версионируются все его эндпоинты
router = APIRouter(dependencies=[Depends(versioning())])

@router.get('/router-endpoint')
def router_endpoint() -> None: ...

v1_app.include_router(router)
```

## Чтение метаданных в эндпоинте

Зависимость можно внедрить в эндпоинт — тогда она возвращает именованный кортеж `VersionInfo` с разрешённой конфигурацией версионирования роута:

- `origin` — версия, в которой эндпоинт объявлен;
- `until` — последняя версия, в которой эндпоинт доступен. Если `until` не задавался явно, это последняя существующая версия API.

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi_easy_versioning import VersionInfo, versioning

v1_app = FastAPI(api_version=1)

@v1_app.get('/endpoint')
def endpoint(version: Annotated[VersionInfo, Depends(versioning())]) -> str:
    return f"Доступен с версии {version.origin} до версии {version.until}"
```

Инъекция работает и в WebSocket-эндпоинтах:

```python
from typing import Annotated

from fastapi import Depends, FastAPI, WebSocket
from fastapi_easy_versioning import VersionInfo, versioning

v1_app = FastAPI(api_version=1)

@v1_app.websocket('/ws')
async def ws_endpoint(
    websocket: WebSocket,
    version: Annotated[VersionInfo, Depends(versioning())],
) -> None:
    await websocket.accept()
    await websocket.send_text(f"Доступен с версии {version.origin}")
    await websocket.close()
```

## Диагностика

Если версионирование не инициализировано, попытка внедрить `VersionInfo` завершится `RuntimeError` с перечислением возможных причин:

- `VersioningMiddleware` не добавлен в приложение, монтирующее версии;
- у субприложения не задан `FastAPI(api_version=<int>)`;
- роут зарегистрирован после первого запроса, а `rebuild_versioning` не вызывался.
