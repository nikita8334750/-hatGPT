from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from aiogram import Bot
from redis import Redis
from rq import Queue
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Task, User
from app.db.session import SessionLocal
from app.services.scheduler.reminder_engine import apply_dnd, next_recurrence

settings = get_settings()
logger = get_logger(component="tick_worker")


async def _send(bot: Bot, chat_id: int, message: str) -> None:
    await bot.send_message(chat_id=chat_id, text=message)


def tick() -> int:
    now = datetime.now(timezone.utc)
    sent = 0
    bot = Bot(token=settings.bot_token)
    session: Session = SessionLocal()
    try:
        tasks = session.scalars(
            select(Task)
            .where(Task.status == "active", Task.next_run_at != None, Task.next_run_at <= now)
            .with_for_update(skip_locked=True)
        ).all()
        for task in tasks:
            user = session.get(User, task.user_id)
            if not user:
                continue
            local_due = task.next_run_at
            message = f"⏰ {task.title}"
            asyncio.run(_send(bot, user.telegram_id, message))
            sent += 1
            if task.recurrence:
                next_at = next_recurrence(task.next_run_at, task.recurrence)
                next_at = apply_dnd(user.timezone, next_at, user.dnd_start, user.dnd_end)
                task.next_run_at = next_at
            else:
                task.next_run_at = None
            session.add(task)
        session.commit()
    finally:
        session.close()
        asyncio.run(bot.session.close())
    return sent


def enqueue_tick(redis: Redis) -> None:
    queue = Queue("scheduler", connection=redis)
    queue.enqueue(tick)
