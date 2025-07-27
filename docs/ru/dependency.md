# Зависимость для версионирования

Зависимость `VersioningSupport` и порождающая её фабрика `versioning` являются основным механизмом настройки и параметризации версионирования API.

Фабрика `versioning` позволяет указать версию API, до которой включительно эндпоинт будет добавляться в последующие субприложения FastAPI. Если вызвать фабрику без аргументов или передать в неё значение `None`, эндпоинт будет присутствовать во всех следующих версиях API.

## Использование зависимости

Рекомендуется создавать зависимость через фабрику `versioning`. Зависимость можно добавлять во всех местах, которые поддерживает интерфейс FastAPI.

```python
from fastapi import FastAPI, Depends
from fastapi_easy_versioning import versioning

v1_app = FastAPI(api_version=1)

@v1_app.get('/decorated-endpoint', dependencies=[Depends(versioning())])
def endpoint() -> None: ...

# Также можно добавлять через метод add_api_route приложения
v1_app.add_api_route('/app-add_api_route-call-endpoint', endpoint, dependencies=[Depends(versioning())])

# Или напрямую через роутер
v1_app.router.add_api_route('/router-add_api_route-call-endpoint', endpoint, dependencies=[Depends(versioning())])
```

Зависимость можно добавить сразу во весь роутер при инициализации отдельного роутера или всего FastAPI-приложения. В этом случае все эндпоинты, добавленные в него, будут участвовать в версионировании в соответствии с настройками фабрики.

```python
from fastapi import FastAPI, Depends, APIRouter
from fastapi_easy_versioning import versioning

v1_app = FastAPI(api_version=1)
v2_app = FastAPI(api_version=2, dependencies=[Depends(versioning(until=2))])

router = APIRouter(dependencies=[Depends(versioning())])
v1_app.include_router(router)
```

## Получение данных из зависимости

Зависимость можно внедрить в эндпоинт с использованием синтаксиса `Annotated` или традиционного механизма внедрения зависимостей.

```python
from fastapi import FastAPI, Depends
from typing import Annotated
from fastapi_easy_versioning import VersioningSupport, versioning

v1_app = FastAPI(api_version=1)

@v1_app.get('/endpoint')
def endpoint(version: Annotated[VersioningSupport, Depends(versioning())]) -> str:
    return f"Доступен с версии {version.origin} до версии {version.until}"
```

В этом случае становится доступной конфигурация версионирования для чтения:

- `origin` – номер версии, с которой был добавлен эндпоинт
- `until` – номер версии, до которой включительно доступен эндпоинт. Если не указан явно, будет установлена последняя доступная версия API.
