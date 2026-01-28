from __future__ import annotations

from datetime import datetime, timezone, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from redis import Redis
from sqlalchemy.orm import Session

from app.bot.keyboards import start_keyboard, task_card_keyboard
from app.core.config import get_settings
from app.core.idempotency import RateLimiter
from app.core.logging import get_logger
from app.db.repositories import (
    add_audit_log,
    create_note,
    create_task,
    find_task_by_id,
    get_or_create_user,
    list_active_tasks,
    update_task,
)
from app.services.nlu.dialog_manager import DialogManager
from app.services.nlu.entity_extractor import EntityExtractor
from app.services.nlu.intent_classifier import IntentClassifier
from app.services.scheduler.reminder_engine import apply_dnd
from app.services.summarizer.action_items import extract_action_items
from app.services.summarizer.textrank import summarize

router = Router()
settings = get_settings()
logger = get_logger(component="bot_handlers")


@router.message(Command("start"))
async def cmd_start(message: Message, session: Session, redis: Redis) -> None:
    user = get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        timezone=settings.default_timezone,
        dnd_start=settings.dnd_start,
        dnd_end=settings.dnd_end,
    )
    add_audit_log(session, user.id, "start", {"chat": message.chat.id})
    await message.answer(
        "Привет! Я умный помощник без нейросетей. Напишите задачу или напоминание.",
        reply_markup=start_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Команды: /start, /help, /plan, /list, /settings.\n"
        "Можно писать свободным текстом: 'напомни завтра в 10 позвонить маме'."
    )


@router.message(Command("plan"))
async def cmd_plan(message: Message, session: Session) -> None:
    user = get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        timezone=settings.default_timezone,
        dnd_start=settings.dnd_start,
        dnd_end=settings.dnd_end,
    )
    tasks = list_active_tasks(session, user.id)
    if not tasks:
        await message.answer("На сегодня задач нет.")
        return
    lines = ["План на день:"]
    for task in tasks[:10]:
        due = task.due_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M") if task.due_at else "без срока"
        lines.append(f"• {task.title} (⏰ {due})")
    await message.answer("\n".join(lines))


@router.message(Command("list"))
async def cmd_list(message: Message, session: Session) -> None:
    user = get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        timezone=settings.default_timezone,
        dnd_start=settings.dnd_start,
        dnd_end=settings.dnd_end,
    )
    tasks = list_active_tasks(session, user.id)
    if not tasks:
        await message.answer("Список пуст.")
        return
    for task in tasks[:10]:
        due_local = task.due_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M") if task.due_at else "без срока"
        text = (
            f"📝 {task.title}\n"
            f"⏰ {due_local}\n"
            f"🔁 {task.recurrence or '—'}\n"
            f"🏷 {', '.join(task.tags) if task.tags else '—'}\n"
            f"⭐ {task.priority}\n"
            f"ID: {task.id}"
        )
        await message.answer(text, reply_markup=task_card_keyboard(task.id))


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    await message.answer(
        "Настройки пока в разработке. Можно задать тихие часы и часовой пояс через .env"
    )


@router.callback_query(F.data.startswith("done:"))
async def cb_done(callback: CallbackQuery, session: Session) -> None:
    task_id = int(callback.data.split(":")[1])
    task = find_task_by_id(session, callback.from_user.id, task_id)
    if not task:
        await callback.message.answer("Задача не найдена.")
        await callback.answer()
        return
    task.status = "done"
    update_task(session, task)
    await callback.message.answer("✅ Отмечено выполненным.")
    await callback.answer()


@router.callback_query(F.data.startswith("snooze:"))
async def cb_snooze(callback: CallbackQuery, session: Session) -> None:
    _, task_id_raw, minutes_raw = callback.data.split(":")
    task = find_task_by_id(session, callback.from_user.id, int(task_id_raw))
    if not task:
        await callback.message.answer("Задача не найдена.")
        await callback.answer()
        return
    minutes = int(minutes_raw)
    task.next_run_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    update_task(session, task)
    await callback.message.answer(f"Перенесено на {minutes} минут.")
    await callback.answer()


@router.callback_query(F.data.startswith("tomorrow:"))
async def cb_tomorrow(callback: CallbackQuery, session: Session) -> None:
    task_id = int(callback.data.split(":")[1])
    task = find_task_by_id(session, callback.from_user.id, task_id)
    if not task:
        await callback.message.answer("Задача не найдена.")
        await callback.answer()
        return
    tomorrow = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    task.next_run_at = tomorrow
    update_task(session, task)
    await callback.message.answer("Перенесено на завтра 10:00.")
    await callback.answer()


@router.callback_query(F.data.startswith("delete:"))
async def cb_delete(callback: CallbackQuery, session: Session) -> None:
    task_id = int(callback.data.split(":")[1])
    task = find_task_by_id(session, callback.from_user.id, task_id)
    if not task:
        await callback.message.answer("Задача не найдена.")
        await callback.answer()
        return
    task.status = "deleted"
    update_task(session, task)
    await callback.message.answer("🗑 Задача удалена.")
    await callback.answer()


@router.message()
async def free_text_handler(message: Message, session: Session, redis: Redis) -> None:
    limiter = RateLimiter(redis)
    if not limiter.allow(f"rate:{message.from_user.id}"):
        await message.answer("Слишком много запросов, попробуйте позже.")
        return

    user = get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        timezone=settings.default_timezone,
        dnd_start=settings.dnd_start,
        dnd_end=settings.dnd_end,
    )

    dialog = DialogManager(redis)
    state = dialog.get_state(user.id)
    classifier = IntentClassifier()
    extractor = EntityExtractor(user.timezone)
    intents = classifier.classify(message.text)
    top_intent = intents[0] if intents else None

    if state and state.state == "awaiting_time":
        entities = extractor.extract(message.text)
        if entities.due_at:
            task_id = state.payload.get("task_id")
            task = find_task_by_id(session, user.id, task_id)
            if task:
                task.due_at = entities.due_at
                task.next_run_at = apply_dnd(user.timezone, entities.due_at, user.dnd_start, user.dnd_end)
                update_task(session, task)
                dialog.clear_state(user.id)
                await message.answer("Время сохранено.")
                return
        await message.answer("Не вижу времени, попробуйте ещё раз.")
        return

    if top_intent and top_intent.intent == "summarize":
        summary = summarize(message.text)
        actions = extract_action_items(message.text)
        response = "\n".join(["Кратко:"] + summary)
        if actions:
            response += "\n\nNext steps:\n" + "\n".join(f"- {item}" for item in actions[:5])
        await message.answer(response)
        return

    if top_intent and top_intent.intent == "create_note":
        note = create_note(session, user.id, title="Заметка", content=message.text, tags=[])
        await message.answer(f"Заметка сохранена (ID {note.id}).")
        return

    if top_intent and top_intent.intent in {"list_tasks", "plan_day"}:
        await cmd_list(message, session)
        return

    entities = extractor.extract(message.text)
    if top_intent and top_intent.intent == "create_task":
        task = create_task(
            session,
            user.id,
            title=entities.text,
            due_at=entities.due_at,
            next_run_at=apply_dnd(user.timezone, entities.due_at, user.dnd_start, user.dnd_end)
            if entities.due_at
            else None,
            recurrence=entities.recurrence,
            tags=entities.tags or [],
            priority=entities.priority or "normal",
        )
        add_audit_log(session, user.id, "create_task", {"task_id": task.id})
        suggestions = []
        if not entities.due_at:
            suggestions.append("Хочешь поставить время?")
        if entities.priority == "high":
            suggestions.append("Приоритет пометил как высокий.")
        if entities.tags:
            suggestions.append(f"Добавлены теги: {', '.join(entities.tags)}")
        response = f"Задача создана (ID {task.id})."
        if suggestions:
            response += "\n" + "\n".join(suggestions)
        await message.answer(response, reply_markup=task_card_keyboard(task.id))
        if not entities.due_at:
            dialog.set_state(user.id, "awaiting_time", {"task_id": task.id})
        return

    await message.answer("Не понял запрос. Попробуйте уточнить или используйте /help.")
