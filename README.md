# Smart Telegram Assistant (No-LLM)

Умный Telegram-бот‑помощник, который ощущается как нейросеть, но работает без LLM/нейросетей. В основе — правила, классический NLP, поиск, суммаризация (TextRank), диалоговый менеджер и устойчивый планировщик напоминаний.

## Возможности (MVP)

- Понимание естественного текста (без команд) и классификация намерений.
- Создание задач/напоминаний из фраз: "напомни завтра в 10 позвонить маме".
- Повторения: daily/weekly/weekday/monthly + интервал.
- Умные предложения: попросить время, поставить приоритет, добавить теги.
- Суммаризация длинного текста (TextRank) + next steps.
- Поиск по задачам/заметкам (BM25 + лемматизация + fuzzy).
- Контекст сессии + уточняющие вопросы при неоднозначности.
- Idempotency update_id, rate limiting, AuditLog.

## Быстрый старт

### 1) Получить токен
Создайте бота через @BotFather и получите `BOT_TOKEN`.

### 2) Скопировать `.env`

```bash
cp .env.example .env
```

Заполните значения в `.env` (BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET).

### 3) Запуск docker-compose

```bash
docker-compose up --build
```

### 4) Применить миграции

```bash
docker-compose exec app alembic upgrade head
```

### 5) Настроить webhook

Webhook устанавливается автоматически на старте приложения. Проверьте:

```
GET https://<ваш-домен>/webhook/<WEBHOOK_SECRET>
```

### 6) Проверка

- Откройте бот в Telegram и отправьте `/start`.
- Напишите: `напомни завтра в 10 позвонить маме`.
- Проверьте `/list` и `/plan`.

## Команды

- `/start` — приветствие + кнопки.
- `/help` — помощь.
- `/plan` — план на день.
- `/list` — список задач.
- `/settings` — настройки (через `.env`).

## Архитектура

```
app/
  main.py
  bot/ (handlers, keyboards, middlewares)
  core/ (config, logging, idempotency)
  db/ (models, repositories, migrations)
  services/
    nlu/ (intent_classifier, entity_extractor, dialog_manager)
    scheduler/ (reminder_engine, tick_worker)
    summarizer/ (textrank, action_items)
    search/ (bm25 + lemmatization)
    integrations/ (calendar stub)
  tests/
```

## Планировщик напоминаний

- В БД хранится `next_run_at`.
- Планировщик каждые 30 секунд ставит задачу в очередь RQ.
- Воркер берёт задания и отправляет напоминания.
- DND учитывается при вычислении `next_run_at`.

## Безопасность

- Idempotency по `update_id`.
- Secret webhook path + заголовок.
- Ограничение запросов per user через Redis.
- В логах — только структура, без пользовательских текстов.

## Тесты

```bash
pytest
```

## Ограничения

- Без LLM и нейросетей (строго).
- Интеграции (календарь/почта) — заглушки.

