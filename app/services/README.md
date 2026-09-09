# Services Module

Модуль бизнес-логики приложения.

## 📋 Обзор

Этот модуль содержит основную бизнес-логику приложения: конвертация валют, управление провайдерами, фоновое обновление курсов, отслеживание изменений и работа с историей.

## 🏗️ Архитектура

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Bot Handlers   │────▶│  ConversionSvc   │────▶│  RedisStore     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │ ProviderManager  │
         │              └──────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│  WatchesSvc     │     │    Updater       │
│  (Alerts)       │     │  (Background)    │
└─────────────────┘     └──────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│  HistorySvc     │────▶│   PostgreSQL     │
│  (Optional)     │     │   (History)      │
└─────────────────┘     └──────────────────┘
```

## 📁 Файлы модуля

### `conversion.py`

Сервис конвертации валют.

#### Зависимости
- `dataclasses` (стандартная библиотека Python) - Классы данных
- `decimal` (стандартная библиотека Python) - Точная работа с десятичными числами
- Внутренние:
  - `app.storage.models.RatesSnapshot` - Модель снимка курсов

#### Классы

##### `ConversionResult`

Класс данных для результата конвертации.

**Атрибуты:**
- `amount: Decimal` - Исходная сумма
- `rate: Decimal` - Курс конвертации
- `converted: Decimal` - Конвертированная сумма

#### Функции

##### `get_rate(snapshot: RatesSnapshot, from_ccy: str, to_ccy: str) -> Decimal`

Получает курс конвертации между двумя валютами.

**Логика:**
1. Если `from_ccy == to_ccy` → возвращает 1
2. Если базовая валюта = `from_ccy` → возвращает прямой курс `to_ccy`
3. Если базовая валюта = `to_ccy` → возвращает обратный курс `1 / from_ccy`
4. Иначе → кросс-курс через базовую валюту: `rates[to_ccy] / rates[from_ccy]`

**Исключения:**
- `KeyError` - Если одна из валют не найдена в снимке

**Пример:**
```python
snapshot = RatesSnapshot(
    base="USD",
    rates={"EUR": Decimal("0.9250"), "GBP": Decimal("0.7850")},
    provider="near-real-time",
    as_of="2024-01-15T10:30:00Z",
    fetched_at="2024-01-15T10:30:05Z"
)

rate = get_rate(snapshot, "EUR", "GBP")
# Результат: 0.7850 / 0.9250 = 0.8486
```

##### `convert_amount(snapshot, amount, from_ccy, to_ccy) -> ConversionResult`

Конвертирует сумму из одной валюты в другую.

**Возвращает:** `ConversionResult` с полями `amount`, `rate`, `converted`

**Пример:**
```python
result = convert_amount(snapshot, Decimal("100"), "USD", "EUR")
# result.amount = 100
# result.rate = 0.9250
# result.converted = 92.50
```

##### `format_decimal(value: Decimal, precision: int) -> str`

Форматирует десятичное число с указанной точностью.

**Параметры:**
- `value: Decimal` - Число для форматирования
- `precision: int` - Количество знаков после запятой (2, 4, 6)

**Округление:** ROUND_HALF_UP (математическое округление)

**Пример:**
```python
format_decimal(Decimal("1.234567"), 2)  # "1.23"
format_decimal(Decimal("1.234567"), 4)  # "1.2346"
format_decimal(Decimal("1.234567"), 6)  # "1.234567"
```

---

### `provider_manager.py`

Менеджер провайдеров с паттерном Circuit Breaker.

#### Зависимости
- `dataclasses` (стандартная библиотека Python)
- `datetime` (стандартная библиотека Python)
- `logging` (стандартная библиотека Python)
- Внутренние:
  - `app.providers.base.RatesProvider` - Базовый класс провайдера

#### Классы

##### `ProviderState`

Класс данных для хранения состояния провайдера.

**Атрибуты:**
- `failure_count: int` - Счётчик неудачных попыток
- `fallback_until: datetime | None` - Время окончания fallback режима

##### `ProviderManager`

Управляет переключением между основным и резервным провайдерами.

**Конструктор:**
```python
def __init__(self, primary: RatesProvider, fallback: RatesProvider)
```

**Методы:**

###### `active_provider() -> RatesProvider`
Возвращает активного провайдера (primary или fallback).

###### `record_success() -> None`
Регистрирует успешный запрос, сбрасывает счётчик неудач.

###### `record_failure() -> None`
Регистрирует неудачу, увеличивает счётчик.
При достижении 5 неудач включает fallback режим на 10 минут.

###### `provider_name() -> str`
Возвращает имя активного провайдера.

**Логика Circuit Breaker:**
```
┌─────────────┐      5 ошибок     ┌─────────────┐
│   Primary   │ ────────────────▶ │   Fallback  │
│  (Active)   │                   │  (Active)   │
└─────────────┘                   └─────────────┘
      ▲                                 │
      │ success                         │ 10 минут
      └─────────────────────────────────┘
```

---

### `updater.py`

Сервис фонового обновления курсов валют.

#### Зависимости
- `asyncio` (стандартная библиотека Python)
- `logging` (стандартная библиотека Python)
- `datetime` (стандартная библиотека Python)
- `typing` (стандартная библиотека Python)
- `aiogram.Bot` - Telegram бот для уведомлений
- Внутренние:
  - `app.services.provider_manager.ProviderManager`
  - `app.services.watches.evaluate_watches`
  - `app.storage.models.RatesSnapshot`
  - `app.storage.redis_store.RedisStore`

#### Функции

##### `run_updater(bot, store, manager, base, interval_seconds, cooldown_seconds, history_writer)`

Запускает бесконечный цикл обновления курсов.

**Параметры:**
- `bot: Bot` - Telegram бот для отправки уведомлений
- `store: RedisStore` - Хранилище данных
- `manager: ProviderManager` - Менеджер провайдеров
- `base: str` - Базовая валюта по умолчанию
- `interval_seconds: int` - Интервал между обновлениями
- `cooldown_seconds: int` - Задержка между уведомлениями watch
- `history_writer: Callable | None` - Опциональная функция записи истории

**Логика:**
1. Получает список всех базовых валют из Redis
2. Для каждой базовой валюты вызывает `update_once()`
3. Ждёт `interval_seconds` и повторяет

##### `update_once(bot, store, manager, base, cooldown_seconds, history_writer)`

Выполняет однократное обновление курсов.

**Шаги:**
1. Получает актуальный провайдер из менеджера
2. Запрашивает курсы через `provider.get_latest(base)`
3. Создаёт снимок `RatesSnapshot`
4. Сохраняет снимок в Redis
5. Обновляет информацию о здоровье системы
6. Опционально записывает историю
7. Проверяет watch alerts
8. Регистрирует успех/неудачу в менеджере

---

### `watches.py`

Сервис отслеживания изменений курсов валют.

#### Зависимости
- `dataclasses` (стандартная библиотека Python)
- `datetime` (стандартная библиотека Python)
- `decimal` (стандартная библиотека Python)
- `uuid` (стандартная библиотека Python)
- `logging` (стандартная библиотека Python)
- `aiogram.Bot` - Telegram бот для уведомлений
- Внутренние:
  - `app.services.conversion.get_rate`
  - `app.storage.models.RatesSnapshot`
  - `app.storage.redis_store.RedisStore`

#### Классы

##### `Watch`

Класс данных для отслеживания курса.

**Атрибуты:**
- `id: str` - Уникальный идентификатор (8 символов UUID)
- `from_ccy: str` - Валюта источника
- `to_ccy: str` - Целевая валюта
- `watch_type: str` - Тип: "target" или "percent"
- `target: str` - Целевое значение (число или процент)
- `baseline_rate: str` - Базовый курс на момент создания
- `created_at: str` - Время создания (ISO 8601)
- `last_notified_at: str | None` - Время последнего уведомления

#### Функции

##### `add_watch(store, chat_id, from_ccy, to_ccy, target, baseline_rate) -> Watch`

Добавляет новое отслеживание для чата.

**Параметры:**
- `store: RedisStore` - Хранилище данных
- `chat_id: int` - ID чата Telegram
- `from_ccy: str` - Валюта источника
- `to_ccy: str` - Целевая валюта
- `target: str` - Целевое значение (например, "1.1" или "2%")
- `baseline_rate: Decimal` - Базовый курс

**Возвращает:** `Watch` - Созданное отслеживание

##### `evaluate_watches(bot, store, snapshot, cooldown_seconds)`

Проверяет все активные отслеживания и отправляет уведомления.

**Логика проверки:**
1. Получает список чатов с активными watches
2. Для каждого чата получает список watches
3. Проверяет cooldown (не чаще чем `cooldown_seconds`)
4. Получает текущий курс валютной пары
5. **Для типа "target"**: Проверяет достижение целевого курса
6. **Для типа "percent"**: Проверяет изменение на заданный процент
7. При срабатывании отправляет уведомление в Telegram

**Типы срабатывания:**

| Тип | Условие | Пример |
|-----|---------|--------|
| `target` | Курс пересёк целевое значение | `1.05 <= 1.10 <= 1.15` |
| `percent` | Изменение >= заданному проценту | `|change| >= 2%` |

---

### `history.py`

Сервис хранения истории курсов в PostgreSQL.

#### Зависимости
- `dataclasses` (стандартная библиотека Python)
- `datetime` (стандартная библиотека Python)
- `asyncpg` >= 0.29.0 - Асинхронный драйвер PostgreSQL
- Внутренние:
  - `app.storage.models.RatesSnapshot`

#### Классы

##### `HistoryConfig`

Конфигурация сервиса истории.

**Атрибуты:**
- `dsn: str` - Connection string PostgreSQL

##### `HistoryWriter`

Класс для записи и чтения истории курсов.

**Конструктор:**
```python
def __init__(self, config: HistoryConfig)
```

**Методы:**

###### `connect() -> None`
Подключается к PostgreSQL и создаёт таблицу если не существует.

**Схема таблицы:**
```sql
CREATE TABLE IF NOT EXISTS rates_history (
    id serial primary key,
    base text,
    quote text,
    rate numeric,
    as_of timestamptz,
    provider text,
    fetched_at timestamptz
)
```

###### `write_snapshot(snapshot: RatesSnapshot) -> None`
Записывает снимок курсов в базу данных.

**Логика:**
- Для каждой валютной пары в снимке создаётся отдельная запись
- Запись содержит: base, quote, rate, as_of, provider, fetched_at

###### `get_history(base, quote, window) -> list[tuple[str, str, str]]`
Получает историю курсов за указанный период.

**Параметры:**
- `base: str` - Базовая валюта
- `quote: str` - Целевая валюта
- `window: str` - Период: "24h" или "7d"

**Возвращает:** Список кортежей `(rate, as_of)`

**SQL запрос:**
```sql
SELECT rate, as_of
FROM rates_history
WHERE base=$1 AND quote=$2 AND as_of >= $3
ORDER BY as_of DESC
LIMIT 10
```

---

## 🔧 Использование

### Конвертация валют

```python
from decimal import Decimal
from app.services.conversion import convert_amount, format_decimal, get_rate

# Получить курс
rate = get_rate(snapshot, "EUR", "USD")
print(f"EUR/USD: {format_decimal(rate, 4)}")

# Конвертировать сумму
result = convert_amount(snapshot, Decimal("100"), "EUR", "USD")
print(f"{result.amount} EUR = {format_decimal(result.converted, 2)} USD")
```

### Управление провайдерами

```python
from app.providers.near_real_time import NearRealTimeProvider
from app.providers.free_fallback import FreeFallbackProvider
from app.services.provider_manager import ProviderManager

primary = NearRealTimeProvider("api_key", "https://api.example.com/latest")
fallback = FreeFallbackProvider()
manager = ProviderManager(primary, fallback)

try:
    provider = manager.active_provider()
    as_of, rates = await provider.get_latest("USD")
    manager.record_success()
except Exception:
    manager.record_failure()
```

### Добавление отслеживания

```python
from app.services.watches import add_watch, evaluate_watches
from decimal import Decimal

# Добавить watch
watch = await add_watch(
    store=redis_store,
    chat_id=12345,
    from_ccy="USD",
    to_ccy="EUR",
    target="2%",  # Уведомить при изменении на 2%
    baseline_rate=Decimal("0.9250")
)

# Проверить watches (вызывается в updater)
await evaluate_watches(bot, redis_store, snapshot, cooldown_seconds=300)
```

### История курсов

```python
from app.services.history import HistoryConfig, HistoryWriter

# Инициализация
config = HistoryConfig(dsn="postgresql://user:pass@localhost:5432/db")
writer = HistoryWriter(config)
await writer.connect()

# Запись снимка
await writer.write_snapshot(snapshot)

# Чтение истории
history = await writer.get_history("USD", "EUR", "24h")
for rate, as_of in history:
    print(f"{as_of}: {rate}")
```

---

## 🧪 Тестирование

Тесты для модуля находятся в `/workspace/tests/`:

- `test_conversion.py` - Тесты конвертации валют
- `test_failover.py` - Тесты переключения провайдеров
- `test_updater_integration.py` - Интеграционные тесты updater

### Запуск тестов

```bash
# Все тесты
pytest

# Только тесты конвертации
pytest tests/test_conversion.py -v

# Интеграционные тесты
pytest tests/test_updater_integration.py -v

# С покрытием кода
pytest --cov=app/services
```

### Пример теста

```python
import pytest
from decimal import Decimal
from app.services.conversion import convert_amount, get_rate

@pytest.mark.asyncio
async def test_conversion():
    snapshot = RatesSnapshot(
        base="USD",
        rates={"EUR": Decimal("0.9250")},
        provider="test",
        as_of="2024-01-15T10:30:00Z",
        fetched_at="2024-01-15T10:30:05Z"
    )
    
    result = convert_amount(snapshot, Decimal("100"), "USD", "EUR")
    
    assert result.amount == Decimal("100")
    assert result.rate == Decimal("0.9250")
    assert result.converted == Decimal("92.50")
```

---

## ⚠️ Важные замечания

1. **Точность вычислений**: Используется `decimal.Decimal` для избежания ошибок floating point
2. **Округление**: ROUND_HALF_UP (математическое округление)
3. **Circuit Breaker**: 5 неудач → 10 минут fallback режима
4. **Cooldown**: Уведомления watch не чаще чем раз в `WATCH_COOLDOWN_SECONDS`
5. **История**: Требует установленного `asyncpg` и подключенного PostgreSQL
6. **Валюты**: Все коды валют приводятся к верхнему регистру

---

## 📊 Производительность

| Операция | Время выполнения | Память |
|----------|-----------------|--------|
| `get_rate()` | < 1ms | O(1) |
| `convert_amount()` | < 1ms | O(1) |
| `add_watch()` | < 5ms | O(1) |
| `evaluate_watches()` | ~10ms * N watches | O(N) |
| `write_snapshot()` | ~50ms * N currencies | O(N) |
| `get_history()` | ~100ms | O(10) |
