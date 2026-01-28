from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings

settings = get_settings()


def parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def apply_dnd(user_tz: str, candidate: datetime, dnd_start: str, dnd_end: str) -> datetime:
    tz = ZoneInfo(user_tz)
    local = candidate.astimezone(tz)
    start = parse_time(dnd_start)
    end = parse_time(dnd_end)
    if start < end:
        in_dnd = start <= local.time() < end
    else:
        in_dnd = local.time() >= start or local.time() < end
    if not in_dnd:
        return candidate
    if start < end:
        local = local.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
    else:
        if local.time() >= start:
            local = (local + timedelta(days=1)).replace(
                hour=end.hour, minute=end.minute, second=0, microsecond=0
            )
        else:
            local = local.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
    return local.astimezone(ZoneInfo("UTC"))


def next_recurrence(run_at: datetime, recurrence: dict) -> datetime:
    interval = recurrence.get("interval", 1)
    if recurrence.get("type") == "daily":
        return run_at + timedelta(days=interval)
    if recurrence.get("type") == "weekly":
        weekday = recurrence.get("weekday")
        if weekday is not None:
            days_ahead = (weekday - run_at.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            return run_at + timedelta(days=days_ahead)
        return run_at + timedelta(weeks=interval)
    if recurrence.get("type") == "weekday":
        next_day = run_at + timedelta(days=1)
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        return next_day
    if recurrence.get("type") == "monthly":
        return run_at + timedelta(days=30 * interval)
    return run_at + timedelta(days=1)
