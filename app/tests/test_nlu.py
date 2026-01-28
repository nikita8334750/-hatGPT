from __future__ import annotations

from datetime import datetime, timezone

from app.services.nlu.entity_extractor import EntityExtractor
from app.services.scheduler.reminder_engine import apply_dnd, next_recurrence


def test_parse_date_relative() -> None:
    extractor = EntityExtractor("Europe/Berlin")
    entities = extractor.extract("напомни завтра в 10")
    assert entities.due_at is not None


def test_recurrence_weekday() -> None:
    extractor = EntityExtractor("Europe/Berlin")
    entities = extractor.extract("каждый понедельник в 9")
    assert entities.recurrence is not None
    assert entities.recurrence["type"] == "weekly"


def test_dnd_shift() -> None:
    candidate = datetime(2024, 1, 1, 23, 0, tzinfo=timezone.utc)
    shifted = apply_dnd("Europe/Berlin", candidate, "22:00", "08:00")
    assert shifted > candidate


def test_next_recurrence_daily() -> None:
    base = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    next_at = next_recurrence(base, {"type": "daily", "interval": 1})
    assert next_at.day == 2
