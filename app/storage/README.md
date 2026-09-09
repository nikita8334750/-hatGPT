# Storage Module

Модуль хранения данных приложения.

## 📋 Обзор

Этот модуль отвечает за хранение и управление данными приложения: снимки курсов валют, информация о здоровье системы, настройки пользователей, отслеживания (watches). Использует Redis как основное хранилище.

## 🏗️ Архитектура

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  App Services   │────▶│   RedisStore     │────▶│    Redis    │
│  (Business Logic)│    │   (Data Access)  │     │   Server    │
└─────────────────┘     └──────────────────┘     └─────────────┘
         │
         │ (Optional)
         ▼
┌─────────────────┐     ┌──────────────────┐
│  HistoryWriter  │────▶│   PostgreSQL     │
│                 │     │   (History)      │
└─────────────────┘     └──────────────────┘
```

## 📁 Файлы модуля

### `models.py`

Модели данных приложения.

#### Зависимости
- `dataclasses` (стандартная библиотека Python) - Классы данных
- `decimal` (стандартная библиотека Python) - Точная работа с десятичными числами

#### Классы

##### `RatesSnapshot`

Класс данных для снимка курсов валют.

**Атрибуты:**
- `base: str` - Код базовой валюты (например, "USD")
- `rates: dict[str, Decimal]` - Словарь кодов валют и их курсов относительно base
- `provider: str` - Имя провайдера, предоставившего данные
- `as_of: str` - Время актуальности курсов (ISO 8601)
- `fetched_at: str` - Время получения данных (ISO 8601)

**Пример:**
```python
snapshot = RatesSnapshot(
    base="USD",
    rates={
        "EUR": Decimal("0.9250"),
        "GBP": Decimal("0.7850"),
        "JPY": Decimal("149.50")
    },
    provider="near-real-time",
    as_of="2024-01-15T10:30:00+00:00",
    fetched_at="2024-01-15T10:30:05+00:00"
)
```

##### `HealthStatus`

Класс данных для статуса здоровья системы.

**Атрибуты:**
- `active_provider: str` - Имя активного провайдера
- `last_success_at: str | None` - Время последнего успешного обновления
- `last_error: str | None` - Сообщение о последней ошибке
- `staleness_seconds: int` - Возраст данных в секундах

**Пример:**
```python
health = HealthStatus(
    active_provider="near-real-time",
    last_success_at="2024-01-15T10:30:05+00:00",
    last_error=None,
    staleness_seconds=60
)
```

---

### `redis_store.py`

Класс для работы с Redis хранилищем.

#### Зависимости
- `json` (стандартная библиотека Python) - Сериализация JSON
- `datetime` (стандартная библиотека Python) - Работа со временем
- `typing` (стандартная библиотека Python) - Типизация
- `redis.asyncio.Redis` >= 5.0.3 - Асинхронный клиент Redis
- Внутренние:
  - `app.storage.models.RatesSnapshot` - Модель снимка курсов
  - `app.storage.models.HealthStatus` - Модель статуса здоровья

#### Классы

##### `RedisStore`

Основной класс для доступа к данным в Redis.

**Конструктор:**
```python
def __init__(self, redis: Redis)
```

**Параметры:**
- `redis: Redis` - Подключение к Redis (aiogram.asyncio.Redis)

#### Методы для работы с курсами валют

##### `set_rates_snapshot(snapshot: RatesSnapshot) -> None`
Сохраняет снимок курсов в Redis.

**Ключи Redis:**
- `rates:{base}` - JSON снимка курсов
- `currencies:{base}` - JSON список доступных валют

**Формат данных:**
```json
{
  "base": "USD",
  "rates": {"EUR": "0.9250", "GBP": "0.7850"},
  "provider": "near-real-time",
  "as_of": "2024-01-15T10:30:00+00:00",
  "fetched_at": "2024-01-15T10:30:05+00:00"
}
```

##### `get_rates_snapshot(base: str) -> RatesSnapshot | None`
Получает снимок курсов для указанной базовой валюты.

**Возвращает:** `RatesSnapshot` или `None` если данные не найдены

##### `get_currencies(base: str) -> list[str]`
Получает список доступных валют для базовой валюты.

---

#### Методы для работы со здоровьем системы

##### `set_health(health: HealthStatus) -> None`
Сохраняет статус здоровья системы.

**Ключ Redis:** `health`

**Формат данных:**
```json
{
  "active_provider": "near-real-time",
  "last_success_at": "2024-01-15T10:30:05+00:00",
  "last_error": null,
  "staleness_seconds": 60
}
```

##### `get_health() -> HealthStatus | None`
Получает текущий статус здоровья системы.

---

#### Методы для работы с настройками чатов

##### `set_chat_base(chat_id: int, base: str) -> None`
Устанавливает базовую валюту по умолчанию для чата.

**Ключи Redis:**
- `chat:{chat_id}:base` - Базовая валюта чата
- `bases` - Set всех используемых базовых валют

##### `get_chat_base(chat_id: int) -> str | None`
Получает базовую валюту чата.

##### `add_base(base: str) -> None`
Добавляет базовую валюту в set известных баз.

##### `list_bases() -> list[str]`
Получает список всех известных базовых валют.

---

#### Методы для работы с точностью вывода

##### `set_chat_precision(chat_id: int, precision: int) -> None`
Устанавливает точность вывода (количество знаков после запятой) для чата.

**Ключ Redis:** `chat:{chat_id}:precision`

**Поддерживаемые значения:** 2, 4, 6

##### `get_chat_precision(chat_id: int) -> int | None`
Получает точность вывода для чата.

---

#### Методы для работы с отслеживаниями (watches)

##### `add_watch(chat_id: int, watch: dict[str, Any]) -> None`
Добавляет новое отслеживание для чата.

**Ключи Redis:**
- `chat:{chat_id}:watches` - JSON список watches
- `watches:chats` - Set ID чатов с активными watches

**Формат watch:**
```json
{
  "id": "abc12345",
  "from_ccy": "USD",
  "to_ccy": "EUR",
  "watch_type": "percent",
  "target": "2%",
  "baseline_rate": "0.9250",
  "created_at": "2024-01-15T10:30:00+00:00",
  "last_notified_at": null
}
```

##### `list_watches(chat_id: int) -> list[dict[str, Any]]`
Получает список всех активных отслеживаний чата.

##### `set_watches(chat_id: int, watches: list[dict[str, Any]]) -> None`
Заменяет список отслеживаний чата.

##### `list_watch_chats() -> list[int]`
Получает список ID всех чатов с активными отслеживаниями.

##### `update_watch_last_notified(chat_id: int, watch_id: str, timestamp: str) -> None`
Обновляет время последнего уведомления для отслеживания.

##### `remove_watch(chat_id: int, watch_id: str) -> bool`
Удаляет отслеживание по ID.

**Возвращает:** `True` если удалено, `False` если не найдено

---

#### Методы для управления ошибками

##### `set_last_error(error: str) -> None`
Записывает информацию о последней ошибке.

##### `set_last_success(provider: str, staleness_seconds: int) -> None`
Записывает информацию об успешном обновлении.

---

## 🔧 Использование

### Инициализация RedisStore

```python
from redis.asyncio import Redis
from app.storage.redis_store import RedisStore

# Создание подключения
redis = Redis.from_url("redis://localhost:6379/0", decode_responses=False)

# Создание хранилища
store = RedisStore(redis)

# Не забудьте закрыть подключение при завершении
await redis.close()
```

### Работа с курсами валют

```python
from decimal import Decimal
from app.storage.models import RatesSnapshot

# Создание снимка
snapshot = RatesSnapshot(
    base="USD",
    rates={"EUR": Decimal("0.9250"), "GBP": Decimal("0.7850")},
    provider="near-real-time",
    as_of="2024-01-15T10:30:00+00:00",
    fetched_at="2024-01-15T10:30:05+00:00"
)

# Сохранение
await store.set_rates_snapshot(snapshot)

# Получение
snapshot = await store.get_rates_snapshot("USD")
if snapshot:
    print(f"EUR rate: {snapshot.rates['EUR']}")

# Список валют
currencies = await store.get_currencies("USD")
print(f"Available: {', '.join(currencies)}")
```

### Настройки чата

```python
# Установка базовой валюты
await store.set_chat_base(chat_id=12345, base="EUR")
await store.add_base("EUR")

# Получение базовой валюты
base = await store.get_chat_base(chat_id=12345)
print(f"Default base: {base}")

# Установка точности
await store.set_chat_precision(chat_id=12345, precision=2)
precision = await store.get_chat_precision(chat_id=12345)
print(f"Precision: {precision}")

# Список всех баз
bases = await store.list_bases()
print(f"All bases: {bases}")
```

### Отслеживания (Watches)

```python
from datetime import datetime, timezone

# Добавление watch
watch = {
    "id": "abc12345",
    "from_ccy": "USD",
    "to_ccy": "EUR",
    "watch_type": "percent",
    "target": "2%",
    "baseline_rate": "0.9250",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "last_notified_at": None
}
await store.add_watch(chat_id=12345, watch=watch)

# Получение списка
watches = await store.list_watches(chat_id=12345)
for watch in watches:
    print(f"{watch['from_ccy']}/{watch['to_ccy']} @ {watch['target']}")

# Обновление времени уведомления
await store.update_watch_last_notified(
    chat_id=12345,
    watch_id="abc12345",
    timestamp=datetime.now(timezone.utc).isoformat()
)

# Удаление
removed = await store.remove_watch(chat_id=12345, watch_id="abc12345")
if removed:
    print("Watch removed")

# Чаты с watches
chat_ids = await store.list_watch_chats()
print(f"Chats with watches: {chat_ids}")
```

### Здоровье системы

```python
from app.storage.models import HealthStatus

# Запись успеха
await store.set_last_success(provider="near-real-time", staleness_seconds=60)

# Запись ошибки
await store.set_last_error("Connection timeout")

# Получение статуса
health = await store.get_health()
if health:
    print(f"Provider: {health.active_provider}")
    print(f"Last success: {health.last_success_at}")
    print(f"Staleness: {health.staleness_seconds}s")
    if health.last_error:
        print(f"Last error: {health.last_error}")
```

---

## 📊 Структура ключей Redis

| Ключ | Тип | Описание |
|------|-----|----------|
| `rates:{base}` | String | JSON снимка курсов для базовой валюты |
| `currencies:{base}` | String | JSON список доступных валют |
| `health` | String | JSON статуса здоровья системы |
| `chat:{chat_id}:base` | String | Базовая валюта чата |
| `chat:{chat_id}:precision` | String | Точность вывода чата |
| `chat:{chat_id}:watches` | String | JSON список watches чата |
| `bases` | Set | Set всех известных базовых валют |
| `watches:chats` | Set | Set ID чатов с активными watches |

---

## 🧪 Тестирование

Тесты для модуля находятся в `/workspace/tests/`:

- `test_currencies.py` - Тесты работы с валютами
- `test_updater_integration.py` - Интеграционные тесты с Redis

### Mock-тестирование с fakeredis

```python
import pytest
import fakeredis.aioredis
from app.storage.redis_store import RedisStore
from app.storage.models import RatesSnapshot
from decimal import Decimal

@pytest.mark.asyncio
async def test_redis_store():
    # Создание mock Redis
    redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
    store = RedisStore(redis)
    
    # Тестирование
    snapshot = RatesSnapshot(
        base="USD",
        rates={"EUR": Decimal("0.9250")},
        provider="test",
        as_of="2024-01-15T10:30:00+00:00",
        fetched_at="2024-01-15T10:30:05+00:00"
    )
    
    await store.set_rates_snapshot(snapshot)
    retrieved = await store.get_rates_snapshot("USD")
    
    assert retrieved is not None
    assert retrieved.base == "USD"
    assert retrieved.rates["EUR"] == Decimal("0.9250")
    
    await redis.close()
```

### Запуск тестов

```bash
# Все тесты
pytest

# Только тесты currencies
pytest tests/test_currencies.py -v

# С подробным выводом
pytest -v --tb=short

# С покрытием кода
pytest --cov=app/storage
```

---

## ⚠️ Важные замечания

1. **Сериализация Decimal**: Decimal значения сериализуются как строки в JSON
2. **Timezone**: Все временные метки в формате ISO 8601 с timezone (UTC)
3. **Атомарность**: Операции с Redis не атомарны на уровне нескольких команд
4. **Память**: Данные в Redis не имеют TTL, рекомендуется настроить очистку
5. **Коннекты**: Обязательно закрывайте подключение к Redis при завершении

---

## 🔗 Полезные ссылки

- [Redis Documentation](https://redis.io/docs/)
- [redis-py Documentation](https://redis.readthedocs.io/)
- [fakeredis for Testing](https://github.com/cunla/fakeredis-py)
