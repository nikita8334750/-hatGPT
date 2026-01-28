from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Note, Task, User


def get_or_create_user(session: Session, telegram_id: int, timezone: str, dnd_start: str, dnd_end: str) -> User:
    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user:
        return user
    user = User(telegram_id=telegram_id, timezone=timezone, dnd_start=dnd_start, dnd_end=dnd_end)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_task(session: Session, user_id: int, title: str, **kwargs) -> Task:
    task = Task(user_id=user_id, title=title, **kwargs)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def list_active_tasks(session: Session, user_id: int) -> list[Task]:
    return list(session.scalars(select(Task).where(Task.user_id == user_id, Task.status == "active").order_by(Task.created_at)))


def update_task(session: Session, task: Task) -> Task:
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def find_task_by_id(session: Session, user_id: int, task_id: int) -> Task | None:
    return session.scalar(select(Task).where(Task.user_id == user_id, Task.id == task_id))


def create_note(session: Session, user_id: int, title: str, content: str, tags: list[str]) -> Note:
    note = Note(user_id=user_id, title=title, content=content, tags=tags)
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


def list_notes(session: Session, user_id: int) -> list[Note]:
    return list(session.scalars(select(Note).where(Note.user_id == user_id).order_by(Note.created_at.desc())))


def add_audit_log(session: Session, user_id: int | None, action: str, payload: dict) -> None:
    entry = AuditLog(user_id=user_id, action=action, payload=payload, created_at=datetime.utcnow())
    session.add(entry)
    session.commit()
