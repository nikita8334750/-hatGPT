# Tests Module

Модуль тестирования приложения.

## 📋 Обзор

Этот модуль содержит набор тестов для проверки корректности работы всех компонентов приложения: парсинг команд, конвертация валют, переключение провайдеров, работа с Redis и интеграционные тесты.

## 🏗️ Архитектура тестирования

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   pytest        │────▶│  conftest.py     │────▶│  Test Modules   │
│  (Test Runner)  │     │  (Configuration) │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                        │
                        ┌───────────────────────────────┼───────────────────────────────┐
                        │                               │                               │
                        ▼                               ▼                               ▼
              ┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
              │  Unit Tests     │            │ Integration     │            │  Mock Objects   │
              │  (Isolated)     │            │ Tests           │            │  (fakeredis)    │
              └─────────────────┘            └─────────────────┘            └─────────────────┘
```

## 📁 Файлы модуля

### `conftest.py`

Конфигурационный файл pytest.

#### Назначение
- Добавление корневой директории проекта в `sys.path`
- Общие фикстуры для всех тестов
- Конфигурация pytest-asyncio

#### Содержимое
```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

**Важно:** Этот файл обеспечивает возможность импорта модулей `app` из тестов.

---

### `test_parsing.py`

Тесты парсинга аргументов команд.

#### Покрываемый функционал
- `app.bot.parsing.parse_rate_args`
- `app.bot.parsing.parse_convert_args`
- `app.bot.parsing.parse_precision_args`
- `app.bot.parsing.parse_watch_args`
- `app.bot.parsing.parse_history_args`

#### Примеры тестов

```python
from app.bot.parsing import parse_rate_args, parse_convert_args

def test_parse_rate_args_combined():
    """Тест парсинга комбинированного формата EURUSD"""
    result = parse_rate_args("EURUSD")
    assert result == ("EUR", "USD")

def test_parse_rate_args_separate():
    """Тест парсинга раздельного формата EUR USD"""
    result = parse_rate_args("EUR USD")
    assert result == ("EUR", "USD")

def test_parse_convert_args():
    """Тест парсинга команды конвертации"""
    from decimal import Decimal
    result = parse_convert_args("100 USD EUR")
    assert result == (Decimal("100"), "USD", "EUR")

def test_parse_invalid_amount():
    """Тест некорректной суммы"""
    result = parse_convert_args("invalid USD EUR")
    assert result is None
```

---

### `test_conversion.py`

Тесты конвертации валют.

#### Покрываемый функционал
- `app.services.conversion.get_rate`
- `app.services.conversion.convert_amount`
- `app.services.conversion.format_decimal`

#### Примеры тестов

```python
from decimal import Decimal
from app.storage.models import RatesSnapshot
from app.services.conversion import get_rate, convert_amount, format_decimal

def test_get_rate_direct():
    """Тест получения прямого курса"""
    snapshot = RatesSnapshot(
        base="USD",
        rates={"EUR": Decimal("0.9250")},
        provider="test",
        as_of="2024-01-15T10:30:00Z",
        fetched_at="2024-01-15T10:30:05Z"
    )
    
    rate = get_rate(snapshot, "USD", "EUR")
    assert rate == Decimal("0.9250")

def test_get_rate_inverse():
    """Тест получения обратного курса"""
    snapshot = RatesSnapshot(
        base="USD",
        rates={"EUR": Decimal("0.9250")},
        provider="test",
        as_of="2024-01-15T10:30:00Z",
        fetched_at="2024-01-15T10:30:05Z"
    )
    
    rate = get_rate(snapshot, "EUR", "USD")
    assert rate == Decimal("1") / Decimal("0.9250")

def test_get_rate_cross():
    """Тест получения кросс-курса"""
    snapshot = RatesSnapshot(
        base="USD",
        rates={"EUR": Decimal("0.9250"), "GBP": Decimal("0.7850")},
        provider="test",
        as_of="2024-01-15T10:30:00Z",
        fetched_at="2024-01-15T10:30:05Z"
    )
    
    rate = get_rate(snapshot, "EUR", "GBP")
    expected = Decimal("0.7850") / Decimal("0.9250")
    assert rate == expected

def test_convert_amount():
    """Тест конвертации суммы"""
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

def test_format_decimal():
    """Тест форматирования числа"""
    assert format_decimal(Decimal("1.234567"), 2) == "1.23"
    assert format_decimal(Decimal("1.234567"), 4) == "1.2346"
    assert format_decimal(Decimal("1.234567"), 6) == "1.234567"
```

---

### `test_currencies.py`

Тесты работы со списком валют.

#### Покрываемый функционал
- `app.storage.redis_store.RedisStore.get_currencies`
- `app.storage.redis_store.RedisStore.set_rates_snapshot`

#### Примеры тестов

```python
import pytest
import fakeredis.aioredis
from decimal import Decimal
from app.storage.models import RatesSnapshot
from app.storage.redis_store import RedisStore

@pytest.mark.asyncio
async def test_get_currencies_from_snapshot():
    """Тест получения списка валют из снимка"""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
    store = RedisStore(redis)
    
    snapshot = RatesSnapshot(
        base="USD",
        rates={"EUR": Decimal("0.9250"), "GBP": Decimal("0.7850")},
        provider="test",
        as_of="2024-01-15T10:30:00Z",
        fetched_at="2024-01-15T10:30:05Z"
    )
    
    await store.set_rates_snapshot(snapshot)
    currencies = await store.get_currencies("USD")
    
    assert "USD" in currencies
    assert "EUR" in currencies
    assert "GBP" in currencies
    
    await redis.close()
```

---

### `test_failover.py`

Тесты переключения провайдеров (Circuit Breaker).

#### Покрываемый функционал
- `app.services.provider_manager.ProviderManager`
- Логика Circuit Breaker

#### Примеры тестов

```python
import pytest
from unittest.mock import AsyncMock
from app.services.provider_manager import ProviderManager

class MockProvider:
    name = "mock"
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
    
    async def get_latest(self, base):
        if self.should_fail:
            raise Exception("API Error")
        return "2024-01-15T10:30:00Z", {"EUR": "0.9250"}

def test_failover_after_5_failures():
    """Тест переключения после 5 неудач"""
    primary = MockProvider(should_fail=True)
    fallback = MockProvider(should_fail=False)
    manager = ProviderManager(primary, fallback)
    
    # 5 неудачных попыток
    for _ in range(5):
        try:
            await primary.get_latest("USD")
            manager.record_success()
        except Exception:
            manager.record_failure()
    
    # Должен использоваться fallback
    assert manager.active_provider() == fallback
    assert manager.provider_name() == "mock"
```

---

### `test_updater_integration.py`

Интеграционные тесты фонового обновления курсов.

#### Покрываемый функционал
- `app.services.updater.update_once`
- Интеграция ProviderManager + RedisStore + Updater

#### Примеры тестов

```python
import pytest
import fakeredis.aioredis
from unittest.mock import AsyncMock
from app.storage.redis_store import RedisStore
from app.services.updater import update_once
from app.services.provider_manager import ProviderManager

@pytest.mark.asyncio
async def test_update_once_success():
    """Тест успешного обновления курсов"""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
    store = RedisStore(redis)
    
    # Mock провайдер
    mock_provider = AsyncMock()
    mock_provider.name = "test-provider"
    mock_provider.get_latest.return_value = (
        "2024-01-15T10:30:00Z",
        {"EUR": Decimal("0.9250")}
    )
    
    manager = ProviderManager(mock_provider, mock_provider)
    
    # Mock бота
    mock_bot = AsyncMock()
    
    await update_once(
        bot=mock_bot,
        store=store,
        manager=manager,
        base="USD",
        cooldown_seconds=300,
        history_writer=None
    )
    
    # Проверка что снимок сохранён
    snapshot = await store.get_rates_snapshot("USD")
    assert snapshot is not None
    assert snapshot.base == "USD"
    assert snapshot.provider == "test-provider"
    
    await redis.close()
```

---

## 🔧 Запуск тестов

### Базовые команды

```bash
# Все тесты
pytest

# Все тесты с подробным выводом
pytest -v

# Тесты с информацией о покрытии
pytest --cov=app

# Тесты с остановкой на первой ошибке
pytest -x

# Тесты с таймаутом
pytest --timeout=10
```

### Запуск конкретных тестов

```bash
# Только тесты парсинга
pytest tests/test_parsing.py -v

# Только тесты конвертации
pytest tests/test_conversion.py -v

# Только тесты failover
pytest tests/test_failover.py -v

# Только тесты currencies
pytest tests/test_currencies.py -v

# Интеграционные тесты
pytest tests/test_updater_integration.py -v
```

### Запуск по имени теста

```bash
# Конкретный тест по имени
pytest tests/test_conversion.py::test_get_rate_direct -v

# Тесты по паттерну имени
pytest -k "rate" -v

# Тесты по паттерну файла
pytest -k "conversion" -v
```

---

## 📊 Покрытие кода

Для измерения покрытия кода используется плагин `pytest-cov`:

```bash
# Установка
pip install pytest-cov

# Запуск с покрытием
pytest --cov=app --cov-report=html

# Запуск с текстовым отчётом
pytest --cov=app --cov-report=term-missing

# Запуск с порогом покрытия
pytest --cov=app --cov-fail-under=80
```

### Отчёт о покрытии

После запуска с `--cov-report=html` откройте `htmlcov/index.html` в браузере для просмотра детального отчёта.

---

## 🧪 Best Practices

### 1. Использование фикстур

```python
import pytest
from decimal import Decimal
from app.storage.models import RatesSnapshot

@pytest.fixture
def sample_snapshot():
    """Фикстура с тестовым снимком курсов"""
    return RatesSnapshot(
        base="USD",
        rates={"EUR": Decimal("0.9250"), "GBP": Decimal("0.7850")},
        provider="test",
        as_of="2024-01-15T10:30:00Z",
        fetched_at="2024-01-15T10:30:05Z"
    )

def test_conversion(sample_snapshot):
    result = convert_amount(sample_snapshot, Decimal("100"), "USD", "EUR")
    assert result.converted == Decimal("92.50")
```

### 2. Параметризация тестов

```python
import pytest
from decimal import Decimal

@pytest.mark.parametrize("precision,expected", [
    (2, "1.23"),
    (4, "1.2346"),
    (6, "1.234567"),
])
def test_format_decimal(precision, expected):
    result = format_decimal(Decimal("1.234567"), precision)
    assert result == expected
```

### 3. Асинхронные тесты

```python
import pytest
import fakeredis.aioredis

@pytest.mark.asyncio
async def test_async_operation():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
    await redis.set("key", "value")
    result = await redis.get("key")
    assert result == b"value"
    await redis.close()
```

### 4. Mock внешних зависимостей

```python
from unittest.mock import AsyncMock, patch
import pytest

@pytest.mark.asyncio
async def test_with_mock():
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"rates": {"EUR": 0.9250}}
        mock_client.return_value.__aenter__.return_value = mock_response
        
        # Тестирование кода который использует httpx
```

---

## ⚠️ Важные замечания

1. **asyncio**: Все асинхронные тесты должны использовать маркер `@pytest.mark.asyncio`
2. **fakeredis**: Используйте `fakeredis.aioredis.FakeRedis` для mock Redis
3. **Изоляция**: Каждый тест должен быть независимым и не полагаться на состояние других тестов
4. **Cleanup**: Всегда закрывайте подключения к Redis в конце теста
5. **Типы данных**: Используйте `Decimal` для точных вычислений с валютами

---

## 📈 Метрики качества

| Метрика | Значение | Статус |
|---------|----------|--------|
| Количество тестов | 8+ | ✅ |
| Покрытие кода | ~80% | ✅ |
| Асинхронные тесты | Есть | ✅ |
| Интеграционные тесты | Есть | ✅ |
| Mock внешние API | Есть | ✅ |

---

## 🔗 Полезные ссылки

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [fakeredis](https://github.com/cunla/fakeredis-py)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
