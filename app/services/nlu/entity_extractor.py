from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import dateparser
from dateparser.search import search_dates
from rapidfuzz import process


@dataclass
class ExtractedEntities:
    text: str
    due_at: datetime | None = None
    recurrence: dict | None = None
    tags: list[str] | None = None
    priority: str | None = None
    duration_minutes: int | None = None
    task_reference: str | None = None


class EntityExtractor:
    def __init__(self, timezone: str) -> None:
        self.timezone = timezone

    def extract(self, text: str) -> ExtractedEntities:
        tags = self._extract_tags(text)
        priority = self._extract_priority(text)
        duration = self._extract_duration(text)
        due_at = self._extract_datetime(text)
        recurrence = self._extract_recurrence(text)
        return ExtractedEntities(
            text=text,
            due_at=due_at,
            recurrence=recurrence,
            tags=tags,
            priority=priority,
            duration_minutes=duration,
            task_reference=self._extract_task_reference(text),
        )

    def _extract_tags(self, text: str) -> list[str]:
        return [tag.strip("#") for tag in re.findall(r"#(\w+)", text)]

    def _extract_priority(self, text: str) -> str | None:
        lowered = text.lower()
        if "срочно" in lowered or "важно" in lowered:
            return "high"
        if "не срочно" in lowered:
            return "low"
        return None

    def _extract_duration(self, text: str) -> int | None:
        match = re.search(r"на\s+(\d+)\s*(минут|час)", text.lower())
        if not match:
            return None
        value = int(match.group(1))
        if "час" in match.group(2):
            return value * 60
        return value

    def _extract_datetime(self, text: str) -> datetime | None:
        settings = {
            "TIMEZONE": self.timezone,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
            "LANGUAGE": "ru",
        }
        found = search_dates(text, settings=settings)
        if found:
            return found[0][1]
        return None

    def _extract_recurrence(self, text: str) -> dict | None:
        lowered = text.lower()
        if "каждый будний" in lowered or "по будням" in lowered:
            return {"type": "weekday", "interval": 1}
        if "каждый день" in lowered or "ежедневно" in lowered:
            return {"type": "daily", "interval": 1}
        weekly_match = re.search(r"каждую неделю|еженедельно", lowered)
        if weekly_match:
            return {"type": "weekly", "interval": 1}
        interval_match = re.search(r"раз в (\d+) (день|дня|недел|месяц)", lowered)
        if interval_match:
            value = int(interval_match.group(1))
            unit = interval_match.group(2)
            if "недел" in unit:
                return {"type": "weekly", "interval": value}
            if "месяц" in unit:
                return {"type": "monthly", "interval": value}
            return {"type": "daily", "interval": value}
        weekday_map = {
            "понедельник": 0,
            "вторник": 1,
            "сред": 2,
            "четверг": 3,
            "пятниц": 4,
            "суббот": 5,
            "воскрес": 6,
        }
        for key, value in weekday_map.items():
            if f"по {key}" in lowered or f"каждый {key}" in lowered:
                return {"type": "weekly", "interval": 1, "weekday": value}
        return None

    def _extract_task_reference(self, text: str) -> str | None:
        lowered = text.lower()
        if "последн" in lowered:
            return "last"
        if "перв" in lowered:
            return "first"
        match = re.search(r"#?(\d+)", lowered)
        if match:
            return match.group(1)
        return None

    def match_task_title(self, query: str, titles: list[str]) -> str | None:
        if not titles:
            return None
        result = process.extractOne(query, titles, score_cutoff=70)
        if not result:
            return None
        return result[0]
