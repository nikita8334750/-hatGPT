from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CalendarEvent:
    title: str
    start_at: datetime
    end_at: datetime


def list_events(user_id: int, start: datetime, end: datetime) -> list[CalendarEvent]:
    return []
