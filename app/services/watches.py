import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from aiogram import Bot

from app.services.conversion import get_rate
from app.storage.redis_store import RatesSnapshot, RedisStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Watch:
    id: str
    from_ccy: str
    to_ccy: str
    watch_type: str
    target: str
    baseline_rate: str
    created_at: str
    last_notified_at: str | None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cooldown_elapsed(last_notified_at: str | None, cooldown_seconds: int) -> bool:
    if not last_notified_at:
        return True
    last_dt = datetime.fromisoformat(last_notified_at)
    return (datetime.now(timezone.utc) - last_dt).total_seconds() >= cooldown_seconds


async def add_watch(
    store: RedisStore,
    chat_id: int,
    from_ccy: str,
    to_ccy: str,
    target: str,
    baseline_rate: Decimal,
) -> Watch:
    watch = Watch(
        id=str(uuid4())[:8],
        from_ccy=from_ccy,
        to_ccy=to_ccy,
        watch_type="percent" if target.endswith("%") else "target",
        target=target,
        baseline_rate=str(baseline_rate),
        created_at=_now_iso(),
        last_notified_at=None,
    )
    await store.add_watch(chat_id, watch.__dict__)
    return watch


async def evaluate_watches(
    bot: Bot,
    store: RedisStore,
    snapshot: RatesSnapshot,
    cooldown_seconds: int,
) -> None:
    chat_ids = await store.list_watch_chats()
    for chat_id in chat_ids:
        watches = await store.list_watches(chat_id)
        for watch in watches:
            if not _cooldown_elapsed(watch.get("last_notified_at"), cooldown_seconds):
                continue
            try:
                rate = get_rate(snapshot, watch["from_ccy"], watch["to_ccy"])
            except KeyError:
                continue
            baseline = Decimal(watch["baseline_rate"])
            triggered = False
            message = ""
            if watch["watch_type"] == "target":
                target_value = Decimal(watch["target"])
                if (baseline <= target_value <= rate) or (baseline >= target_value >= rate):
                    triggered = True
                    message = (
                        f"Watch {watch['id']} triggered: {watch['from_ccy']}/{watch['to_ccy']} "
                        f"is now {rate} (target {target_value})."
                    )
            else:
                percent_value = Decimal(watch["target"].rstrip("%"))
                change = (rate - baseline) / baseline * Decimal("100")
                if abs(change) >= percent_value:
                    triggered = True
                    message = (
                        f"Watch {watch['id']} triggered: {watch['from_ccy']}/{watch['to_ccy']} "
                        f"moved {change:.2f}% (baseline {baseline}, now {rate})."
                    )
            if triggered:
                try:
                    await bot.send_message(chat_id, message)
                    await store.update_watch_last_notified(chat_id, watch["id"], _now_iso())
                except Exception as exc:
                    logger.warning("Failed to notify watch %s: %s", watch["id"], exc)
