# Telegram Currency Converter Bot

A Telegram bot that provides currency conversion with near-real-time updates, provider failover, watch alerts, and optional history storage.

## 📋 Содержание

- [Обзор](#обзор)
- [Возможности](#возможности)
- [Архитектура проекта](#архитектура-проекта)
- [Зависимости](#зависимости)
- [Установка и запуск](#установка-и-запуск)
- [Конфигурация](#конфигурация)
- [Команды бота](#команды-бота)
- [Структура проекта](#структура-проекта)
- [Тестирование](#тестирование)
- [Docker](#docker)

## Обзор

Этот проект представляет собой Telegram-бота для конвертации валют с поддержкой:
- Автоматического обновления курсов валют в фоновом режиме
- Резервного провайдера при сбоях основного API
- Отслеживания изменений курсов (watch alerts)
- Кэширования данных в Redis
- Опционального хранения истории в PostgreSQL

## Возможности

- **Фоновое обновление курсов**: Каждые `UPDATE_INTERVAL_SECONDS` (по умолчанию 60 секунд)
- **Кэширование в Redis**: Снимки курсов, информация о здоровье системы, настройки пользователей
- **Provider Failover**: Circuit breaker с автоматическим переключением на резервный провайдер после 5 неудачных попыток
- **Watch Alerts**: Уведомления при достижении целевого курса или изменении на заданный процент
- **Гибкая точность**: Настройка количества знаков после запятой (2, 4, 6)
- **История курсов**: Опциональное сохранение в PostgreSQL для анализа

## Архитектура проекта

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Telegram Bot  │────▶│   aiogram Router │────▶│  Handlers   │
└─────────────────┘     └──────────────────┘     └─────────────┘
                                                        │
                        ┌───────────────────────────────┼───────────────────────────────┐
                        │                               │                               │
                        ▼                               ▼                               ▼
              ┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
              │  ProviderManager│            │  ConversionSvc  │            │   WatchesSvc    │
              │  (CircuitBreaker)│            │                 │            │                 │
              └─────────────────┘            └─────────────────┘            └─────────────────┘
                        │                               │                               │
                        ▼                               ▼                               ▼
              ┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
              │ NearRealTimeProv│           │  RedisStore     │            │  RedisStore     │
              │ FreeFallbackProv│           │                 │            │                 │
              └─────────────────┘            └─────────────────┘            └─────────────────┘
                                                │
                        ┌───────────────────────┼───────────────────────┐
                        │                       │                       │
                        ▼                       ▼                       ▼
                  ┌──────────┐          ┌──────────────┐        ┌──────────────┐
                  │  Redis   │          │   HistorySvc │        │  PostgreSQL  │
                  │  (Cache) │          │  (Optional)  │        │  (History)   │
                  └──────────┘          └──────────────┘        └──────────────┘
```

## Зависимости

### Основные зависимости

| Пакет | Версия | Описание |
|-------|--------|----------|
| `aiogram` | 3.4.1 | Асинхронный фреймворк для Telegram Bot API |
| `httpx` | 0.27.0 | Асинхронный HTTP-клиент для запросов к API |
| `redis` | 5.0.3 | Клиент Redis для кэширования и хранения состояния |
| `asyncpg` | 0.29.0 | Асинхронный драйвер PostgreSQL (опционально, для истории) |

### Зависимости для тестирования

| Пакет | Версия | Описание |
|-------|--------|----------|
| `pytest` | 8.2.2 | Фреймворк для тестирования |
| `pytest-asyncio` | 0.23.7 | Поддержка асинхронных тестов в pytest |
| `fakeredis` | 2.23.2 | Mock-реализация Redis для тестов |

### Системные требования

- Python 3.12+
- Docker и Docker Compose (для контейнеризации)
- Redis 7+ (включён в docker-compose)
- PostgreSQL 16+ (опционально, для истории)

## Установка и запуск

### Быстрый старт с Docker

```bash
# Экспорт необходимых переменных окружения
export BOT_TOKEN=your_telegram_bot_token
export RATES_API_KEY=your_api_key  # опционально
export PROVIDER_URL=https://api.example.com/latest  # опционально

# Запуск бота
docker-compose up --build
```

### Локальная установка

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Запуск бота
export BOT_TOKEN=your_token
python -m app.main
```

### Запуск с историей (PostgreSQL)

```bash
export ENABLE_HISTORY=true
export POSTGRES_DSN=postgresql://bot:bot@postgres:5432/rates

docker-compose --profile history up --build
```

## Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию | Обязательно |
|------------|----------|--------------|-------------|
| `BOT_TOKEN` | Токен Telegram бота | - | ✅ Да |
| `REDIS_URL` | URL подключения к Redis | `redis://redis:6379/0` | ❌ Нет |
| `PROVIDER_URL` | URL основного API курсов валют | `https://api.example.com/latest` | ❌ Нет |
| `RATES_API_KEY` | API ключ для основного провайдера | - | ❌ Нет |
| `UPDATE_INTERVAL_SECONDS` | Интервал обновления курсов (сек) | `60` | ❌ Нет |
| `DEFAULT_BASE` | Базовая валюта по умолчанию | `USD` | ❌ Нет |
| `MAX_STALENESS_SECONDS` | Порог устаревания курсов (сек) | `3600` | ❌ Нет |
| `WATCH_COOLDOWN_SECONDS` | Задержка между уведомлениями (сек) | `300` | ❌ Нет |
| `RATE_LIMIT_SECONDS` | Лимит команд на чат (сек) | `2` | ❌ Нет |
| `ENABLE_HISTORY` | Включить историю в PostgreSQL | `false` | ❌ Нет |
| `POSTGRES_DSN` | URL подключения к PostgreSQL | - | ❌ Нет |

## Команды бота

| Команда | Описание | Пример |
|---------|----------|--------|
| `/rate` | Получить текущий курс валют | `/rate EURUSD` или `/rate EUR USD` |
| `/convert` | Конвертировать сумму | `/convert 100 USD EUR` |
| `/status` | Показать статус системы | `/status` |
| `/base` | Установить базовую валюту | `/base USD` |
| `/precision` | Установить точность вывода | `/precision 2` (2, 4 или 6) |
| `/watch` | Добавить отслеживание курса | `/watch USD EUR 1.1` или `/watch USD EUR 2%` |
| `/watchlist` | Показать активные отслеживания | `/watchlist` |
| `/unwatch` | Удалить отслеживание | `/unwatch <id>` |
| `/currencies` | Показать доступные валюты | `/currencies` |
| `/history` | Показать историю курсов | `/history USD EUR 24h` (24h или 7d) |
| `/help` | Показать справку | `/help` |

## Структура проекта

```
/workspace/
├── README.md                 # Основная документация
├── requirements.txt          # Зависимости Python
├── Dockerfile               # Docker образ бота
├── docker-compose.yml       # Docker Compose конфигурация
├── app/                     # Основной код приложения
│   ├── __init__.py
│   ├── main.py              # Точка входа, инициализация
│   ├── config.py            # Конфигурация и переменные окружения
│   ├── bot/                 # Telegram bot handlers
│   │   ├── handlers.py      # Обработчики команд
│   │   ├── parsing.py       # Парсинг аргументов команд
│   │   └── rate_limit.py    # Rate limiting для команд
│   ├── providers/           # Провайдеры курсов валют
│   │   ├── base.py          # Базовый класс провайдера
│   │   ├── http.py          # HTTP утилиты с retry
│   │   ├── near_real_time.py # Основной провайдер
│   │   └── free_fallback.py # Резервный провайдер
│   ├── services/            # Бизнес-логика
│   │   ├── conversion.py    # Конвертация валют
│   │   ├── history.py       # История курсов (PostgreSQL)
│   │   ├── provider_manager.py # Управление провайдерами
│   │   ├── updater.py       # Фоновое обновление курсов
│   │   └── watches.py       # Отслеживание курсов
│   └── storage/             # Хранилище данных
│       ├── models.py        # Модели данных
│       └── redis_store.py   # Redis хранилище
└── tests/                   # Тесты
    ├── conftest.py          # Конфигурация pytest
    ├── test_conversion.py   # Тесты конвертации
    ├── test_currencies.py   # Тесты валют
    ├── test_failover.py     # Тесты failover
    ├── test_parsing.py      # Тесты парсинга
    └── test_updater_integration.py # Интеграционные тесты
```

## Тестирование

```bash
# Запуск всех тестов
pytest

# Запуск с подробным выводом
pytest -v

# Запуск конкретного теста
pytest tests/test_conversion.py -v

# Запуск с покрытием кода
pytest --cov=app
```

## Docker

### Сборка образа

```bash
docker build -t currency-bot .
```

### Запуск контейнера

```bash
docker run -e BOT_TOKEN=your_token currency-bot
```

### Docker Compose

```bash
# Запуск всех сервисов
docker-compose up

# Запуск в фоновом режиме
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot

# Остановка
docker-compose down
```

---

## Документация по модулям

Для детальной информации о каждом модуле см.:
- [app/bot/README.md](app/bot/README.md) - Telegram bot handlers
- [app/providers/README.md](app/providers/README.md) - Провайдеры курсов валют
- [app/services/README.md](app/services/README.md) - Бизнес-логика
- [app/storage/README.md](app/storage/README.md) - Хранилище данных
- [tests/README.md](tests/README.md) - Тестирование
