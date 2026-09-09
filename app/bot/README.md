# Telegram Bot Handlers Module

Модуль обработки команд Telegram бота.

## 📋 Обзор

Этот модуль отвечает за обработку входящих сообщений от пользователей Telegram и предоставление им функционала конвертации валют.

## 🏗️ Архитектура

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Telegram User  │────▶│  aiogram Router  │────▶│   handlers.py   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                        │
                        ┌───────────────────────────────┼───────────────────────────────┐
                        │                               │                               │
                        ▼                               ▼                               ▼
              ┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
              │   parsing.py    │            │ rate_limit.py   │            │  Services Call  │
              │  (Argument Parse)│           │  (Rate Limiting)│           │                 │
              └─────────────────┘            └─────────────────┘            └─────────────────┘
```

## 📁 Файлы модуля

### `handlers.py`

Основной файл с обработчиками команд бота.

#### Зависимости
- `aiogram` >= 3.4.1 - Фреймворк для Telegram Bot API
- Внутренние зависимости:
  - `app.bot.parsing` - Парсинг аргументов команд
  - `app.bot.rate_limit` - Ограничение частоты команд
  - `app.services.conversion` - Конвертация валют
  - `app.services.history` - История курсов
  - `app.services.watches` - Отслеживание курсов
  - `app.storage.redis_store` - Redis хранилище

#### Функции

##### `setup_router(store, default_base, max_staleness_seconds, history_writer, rate_limiter)`
Инициализирует роутер и регистрирует все обработчики команд.

**Параметры:**
- `store: RedisStore` - Хранилище данных
- `default_base: str` - Базовая валюта по умолчанию
- `max_staleness_seconds: int` - Порог устаревания курсов
- `history_writer: HistoryWriter | None` - Опциональный писатель истории
- `rate_limiter: RateLimiter | None` - Опциональный ограничитель частоты

**Возвращает:** `Router` - Настроенный роутер aiogram

#### Обработчики команд

| Команда | Функция | Описание |
|---------|---------|----------|
| `/help` | `cmd_help` | Показать справку по командам |
| `/status` | `cmd_status` | Показать статус системы и актуальность курсов |
| `/base` | `cmd_base` | Установить базовую валюту для чата |
| `/precision` | `cmd_precision` | Установить точность вывода (2, 4, 6 знаков) |
| `/rate` | `cmd_rate` | Получить текущий курс валютной пары |
| `/convert` | `cmd_convert` | Конвертировать сумму из одной валюты в другую |
| `/watchlist` | `cmd_watchlist` | Показать активные отслеживания курса |
| `/currencies` | `cmd_currencies` | Показать доступные валюты |
| `/unwatch` | `cmd_unwatch` | Удалить отслеживание по ID |
| `/watch` | `cmd_watch` | Добавить отслеживание курса |
| `/history` | `cmd_history` | Показать историю курсов (требует PostgreSQL) |

---

### `parsing.py`

Модуль парсинга аргументов команд.

#### Зависимости
- `decimal` (стандартная библиотека Python) - Точная работа с десятичными числами

#### Функции

##### `parse_rate_args(text: str) -> tuple[str, str] | None`
Парсит аргументы команды `/rate`.

**Поддерживаемые форматы:**
- `EURUSD` - 6-символьная строка
- `EUR USD` - две отдельные валюты

**Примеры:**
```python
parse_rate_args("EURUSD")      # Returns: ("EUR", "USD")
parse_rate_args("EUR USD")     # Returns: ("EUR", "USD")
parse_rate_args("")            # Returns: None
```

##### `parse_convert_args(text: str) -> tuple[Decimal, str, str] | None`
Парсит аргументы команды `/convert`.

**Формат:** `<amount> <FROM> <TO>`

**Примеры:**
```python
parse_convert_args("100 USD EUR")  # Returns: (Decimal("100"), "USD", "EUR")
parse_convert_args("invalid")       # Returns: None
```

##### `parse_precision_args(text: str) -> int | None`
Парсит аргумент команды `/precision`.

**Поддерживаемые значения:** 2, 4, 6

**Примеры:**
```python
parse_precision_args("2")  # Returns: 2
parse_precision_args("4")  # Returns: 4
parse_precision_args("8")  # Returns: None
```

##### `parse_watch_args(text: str) -> tuple[str, str, str] | None`
Парсит аргументы команды `/watch`.

**Формат:** `<FROM> <TO> <target_rate|delta%>`

**Примеры:**
```python
parse_watch_args("USD EUR 1.1")    # Returns: ("USD", "EUR", "1.1")
parse_watch_args("USD EUR 2%")     # Returns: ("USD", "EUR", "2%")
```

##### `parse_history_args(text: str) -> tuple[str, str, str] | None`
Парсит аргументы команды `/history`.

**Формат:** `<FROM> <TO> <window>`

**Поддерживаемые окна:** `24h`, `7d`

---

### `rate_limit.py`

Модуль ограничения частоты команд (Rate Limiting).

#### Зависимости
- `time` (стандартная библиотека Python) - Монотонное время
- `dataclasses` (стандартная библиотека Python) - Классы данных

#### Классы

##### `RateLimiter`

Класс для ограничения частоты команд на уровне чата.

**Атрибуты:**
- `ttl_seconds: int` - Минимальный интервал между командами (сек)

**Методы:**

###### `allow(chat_id: int) -> bool`
Проверяет, можно ли выполнить команду для данного чата.

**Логика:**
- Если последняя команда была выполнена менее `ttl_seconds` назад → `False`
- Иначе → обновляет время последней команды и возвращает `True`

**Пример использования:**
```python
limiter = RateLimiter(ttl_seconds=2)

if limiter.allow(chat_id=12345):
    # Выполнить команду
    await message.answer("Command executed")
else:
    await message.answer("You're doing that too fast. Please wait a moment.")
```

---

## 🔧 Использование

### Инициализация бота

```python
from aiogram import Bot, Dispatcher
from app.bot.handlers import setup_router
from app.bot.rate_limit import RateLimiter
from app.storage.redis_store import RedisStore
from redis.asyncio import Redis

async def main():
    # Инициализация компонентов
    bot = Bot(token="YOUR_BOT_TOKEN")
    dispatcher = Dispatcher()
    redis = Redis.from_url("redis://localhost:6379/0")
    store = RedisStore(redis)
    
    # Создание роутера с обработчиками
    router = setup_router(
        store=store,
        default_base="USD",
        max_staleness_seconds=3600,
        history_writer=None,  # Или экземпляр HistoryWriter
        rate_limiter=RateLimiter(ttl_seconds=2),
    )
    
    # Регистрация роутера
    dispatcher.include_router(router)
    
    # Запуск polling
    await dispatcher.start_polling(bot)
```

### Добавление новой команды

1. Добавьте обработчик в `handlers.py`:

```python
@router.message(F.text.startswith("/mycommand"))
async def cmd_mycommand(message: Message) -> None:
    if rate_limiter and not rate_limiter.allow(message.chat.id):
        await message.answer("You're doing that too fast. Please wait a moment.")
        return
    
    # Логика команды
    await message.answer("Result")
```

2. Обновите справку в `cmd_help`:

```python
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Commands:\n"
        "/rate EURUSD or /rate EUR USD\n"
        "/convert <amount> <FROM> <TO>\n"
        "/mycommand - Description of new command\n"
        # ... остальные команды
    )
```

---

## 🧪 Тестирование

Тесты для модуля находятся в `/workspace/tests/`:

- `test_parsing.py` - Тесты парсинга аргументов
- `test_conversion.py` - Тесты конвертации
- `test_updater_integration.py` - Интеграционные тесты

### Запуск тестов

```bash
# Все тесты
pytest

# Только тесты парсинга
pytest tests/test_parsing.py -v

# С подробным выводом
pytest -v --tb=short
```

---

## 📝 Примеры использования

### Конвертация валют

```
User: /convert 100 USD EUR
Bot: 92.5000 USD = 85.2500 EUR
     Rate: 0.9250
     Provider: near-real-time
     As of: 2024-01-15T10:30:00+00:00
```

### Получение курса

```
User: /rate EURUSD
Bot: EUR/USD: 1.0850
     Provider: near-real-time
     As of: 2024-01-15T10:30:00+00:00
```

### Настройка точности

```
User: /precision 2
Bot: Precision set to 2 decimals.

User: /rate EURUSD
Bot: EUR/USD: 1.09
```

### Отслеживание курса

```
User: /watch USD EUR 1.1
Bot: Watch abc123 added for USD/EUR at 1.1 (baseline 0.9250).

# Когда курс достигнет 1.1:
Bot: Watch abc123 triggered: USD/EUR is now 1.1000 (target 1.1).
```

---

## ⚠️ Важные замечания

1. **Rate Limiting**: По умолчанию установлен лимит 2 секунды между командами в одном чате
2. **Staleness Warning**: Если курсы старше `MAX_STALENESS_SECONDS`, показывается предупреждение
3. **Precision**: Поддерживаются только значения 2, 4, 6 знаков после запятой
4. **History**: Команда `/history` требует включенного PostgreSQL (`ENABLE_HISTORY=true`)
