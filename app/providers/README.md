# Currency Providers Module

Модуль получения курсов валют из внешних API.

## 📋 Обзор

Этот модуль предоставляет абстракцию для получения актуальных курсов валют из различных источников (провайдеров). Поддерживает основной провайдер с платным API и бесплатный резервный провайдер.

## 🏗️ Архитектура

```
┌─────────────────────┐
│  ProviderManager    │
│  (Circuit Breaker)  │
└─────────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────────────────┐     ┌───────────────────┐
│ NearRealTimeProv  │     │ FreeFallbackProv  │
│ (Primary, Paid)   │     │ (Secondary, Free) │
└───────────────────┘     └───────────────────┘
         │                         │
         ▼                         ▼
┌───────────────────┐     ┌───────────────────┐
│   api.example.com │     │ frankfurter.app   │
│   (Requires API   │     │   (Free, No Key)  │
│      Key)         │     │                   │
└───────────────────┘     └───────────────────┘
```

## 📁 Файлы модуля

### `base.py`

Базовый класс для всех провайдеров курсов валют.

#### Зависимости
- `abc` (стандартная библиотека Python) - Абстрактные базовые классы
- `decimal` (стандартная библиотека Python) - Точная работа с десятичными числами

#### Классы

##### `RatesProvider` (Абстрактный класс)

Базовый класс, определяющий интерфейс для всех провайдеров.

**Атрибуты класса:**
- `name: str` - Идентификатор провайдера

**Абстрактные методы:**

###### `get_latest(base: str) -> tuple[str, dict[str, Decimal]]`
Получает последние курсы валют для указанной базовой валюты.

**Параметры:**
- `base: str` - Код базовой валюты (например, "USD", "EUR")

**Возвращает:**
- `tuple[str, dict[str, Decimal]]`:
  - `str` - Дата/время актуальности курсов (ISO 8601)
  - `dict[str, Decimal]` - Словарь кодов валют и их курсов

**Пример реализации:**
```python
class MyProvider(RatesProvider):
    name = "my-provider"
    
    async def get_latest(self, base: str) -> tuple[str, dict[str, Decimal]]:
        # Реализация запроса к API
        pass
```

---

### `http.py`

Утилиты для HTTP-запросов с автоматическими повторами.

#### Зависимости
- `asyncio` (стандартная библиотека Python) - Асинхронное выполнение
- `typing` (стандартная библиотека Python) - Типизация
- `httpx` >= 0.27.0 - Асинхронный HTTP-клиент

#### Функции

##### `request_with_retries(client, method, url, headers, params, timeout, retries)`

Выполняет HTTP-запрос с экспоненциальной задержкой при ошибках.

**Параметры:**
- `client: httpx.AsyncClient` - HTTP клиент
- `method: str` - HTTP метод (GET, POST, etc.)
- `url: str` - URL запроса
- `headers: dict[str, str] | None` - Заголовки запроса
- `params: dict[str, Any] | None` - Параметры запроса
- `timeout: float` - Таймаут запроса (по умолчанию 5.0 сек)
- `retries: int` - Количество попыток (по умолчанию 3)

**Логика повторных попыток:**
- Начальная задержка: 0.5 сек
- Экспоненциальное увеличение: задержка *= 2 после каждой неудачи
- Максимальное количество попыток: `retries`

**Исключения:**
- `httpx.HTTPError` - Бросается после исчерпания всех попыток

**Пример использования:**
```python
import httpx
from app.providers.http import request_with_retries

async with httpx.AsyncClient() as client:
    response = await request_with_retries(
        client,
        "GET",
        "https://api.example.com/latest",
        headers={"Authorization": "Bearer token"},
        params={"base": "USD"},
        timeout=5.0,
        retries=3,
    )
    data = response.json()
```

---

### `near_real_time.py`

Основной провайдер курсов валют с near-real-time обновлением.

#### Зависимости
- `decimal` (стандартная библиотека Python)
- `httpx` >= 0.27.0
- Внутренние:
  - `app.providers.base` - Базовый класс RatesProvider
  - `app.providers.http` - Утилиты HTTP

#### Классы

##### `NearRealTimeProvider`

Провайдер для работы с платным API курсов валют.

**Атрибуты класса:**
- `name = "near-real-time"`

**Конструктор:**
```python
def __init__(self, api_key: str, base_url: str)
```

**Параметры:**
- `api_key: str` - API ключ для авторизации
- `base_url: str` - URL endpoint API

**Методы:**

###### `get_latest(base: str) -> tuple[str, dict[str, Decimal]]`

Получает курсы валют от основного провайдера.

**Формат запроса:**
```
GET {base_url}?base={base}
Headers: Authorization: Bearer {api_key}
```

**Ожидаемый формат ответа:**
```json
{
  "as_of": "2024-01-15T10:30:00Z",
  "rates": {
    "EUR": 0.9250,
    "GBP": 0.7850,
    ...
  }
}
```

**Пример использования:**
```python
provider = NearRealTimeProvider(
    api_key="your_api_key",
    base_url="https://api.example.com/latest"
)

as_of, rates = await provider.get_latest("USD")
print(f"Rates as of: {as_of}")
print(f"EUR rate: {rates['EUR']}")
```

---

### `free_fallback.py`

Резервный бесплатный провайдер курсов валют.

#### Зависимости
- `decimal` (стандартная библиотека Python)
- `httpx` >= 0.27.0
- Внутренние:
  - `app.providers.base` - Базовый класс RatesProvider
  - `app.providers.http` - Утилиты HTTP

#### Классы

##### `FreeFallbackProvider`

Провайдер для работы с бесплатным API Frankfurter.app.

**Атрибуты класса:**
- `name = "free-fallback"`

**Конструктор:**
```python
def __init__(self, base_url: str = "https://api.frankfurter.app/latest")
```

**Параметры:**
- `base_url: str` - URL endpoint API (по умолчанию Frankfurter)

**Методы:**

###### `get_latest(base: str) -> tuple[str, dict[str, Decimal]]`

Получает курсы валют от бесплатного провайдера.

**Формат запроса:**
```
GET {base_url}?base={base}
```

**Ожидаемый формат ответа:**
```json
{
  "date": "2024-01-15",
  "rates": {
    "EUR": 0.9250,
    "GBP": 0.7850,
    ...
  }
}
```

**Пример использования:**
```python
provider = FreeFallbackProvider()
# или с кастомным URL
provider = FreeFallbackProvider("https://api.exchangerate.host/latest")

as_of, rates = await provider.get_latest("EUR")
```

---

## 🔧 Использование с ProviderManager

ProviderManager управляет переключением между провайдерами с использованием паттерна Circuit Breaker.

```python
from app.providers.near_real_time import NearRealTimeProvider
from app.providers.free_fallback import FreeFallbackProvider
from app.services.provider_manager import ProviderManager

# Создание провайдеров
primary = NearRealTimeProvider(
    api_key="your_api_key",
    base_url="https://api.example.com/latest"
)
fallback = FreeFallbackProvider()

# Создание менеджера
manager = ProviderManager(primary, fallback)

# Получение активного провайдера
provider = manager.active_provider()

# Запрос курсов
as_of, rates = await provider.get_latest("USD")

# Регистрация успеха/неудачи
try:
    as_of, rates = await provider.get_latest("USD")
    manager.record_success()
except Exception:
    manager.record_failure()
    # Автоматическое переключение на fallback после 5 неудач
```

### Логика Circuit Breaker

1. **Нормальное состояние**: Используется primary провайдер
2. **При ошибке**: Увеличивается счётчик неудач (`failure_count`)
3. **После 5 неудач**: Переключение на fallback провайдер на 10 минут
4. **После успеха**: Сброс счётчика и возврат к primary провайдеру

---

## 📊 Сравнение провайдеров

| Характеристика | NearRealTimeProvider | FreeFallbackProvider |
|---------------|---------------------|---------------------|
| **API Key** | Требуется | Не требуется |
| **Стоимость** | Платный | Бесплатный |
| **Частота обновления** | Near-real-time | Ежедневно |
| **Надёжность** | Высокая | Средняя |
| **Количество валют** | 170+ | 32 |
| **Использование** | Основной | Резервный |

---

## 🧪 Тестирование

Тесты для модуля находятся в `/workspace/tests/`:

- `test_failover.py` - Тесты переключения провайдеров
- `test_parsing.py` - Тесты парсинга ответов API

### Запуск тестов

```bash
# Все тесты
pytest

# Только тесты failover
pytest tests/test_failover.py -v

# С подробным выводом
pytest -v --tb=short
```

### Mock-тестирование

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.providers.near_real_time import NearRealTimeProvider

@pytest.mark.asyncio
async def test_get_latest():
    provider = NearRealTimeProvider("test_key", "https://test.api/latest")
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "as_of": "2024-01-15T10:30:00Z",
            "rates": {"EUR": 0.9250}
        }
        mock_client.return_value.__aenter__.return_value = mock_client.return_value
        mock_client.get.return_value = mock_response
        
        as_of, rates = await provider.get_latest("USD")
        
        assert as_of == "2024-01-15T10:30:00Z"
        assert rates["EUR"] == Decimal("0.9250")
```

---

## ⚠️ Важные замечания

1. **API Key**: NearRealTimeProvider требует валидный API ключ
2. **Timeout**: По умолчанию установлен таймаут 5 секунд на запрос
3. **Retries**: Автоматические повторные попытки при ошибках сети (3 попытки)
4. **Circuit Breaker**: После 5 неудач происходит переключение на fallback на 10 минут
5. **Валюты**: Все коды валют приводятся к верхнему регистру

---

## 🔗 Полезные ссылки

- [Frankfurter API](https://www.frankfurter.app/docs/)
- [httpx Documentation](https://www.python-httpx.org/)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
