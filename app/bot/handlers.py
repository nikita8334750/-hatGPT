import logging
from datetime import datetime, timezone
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import Message

from app.bot.parsing import (
    parse_chart_args,
    parse_convert_args,
    parse_history_args,
    parse_movers_args,
    parse_precision_args,
    parse_rate_args,
    parse_trend_args,
    parse_watch_args,
)
from app.bot.rate_limit import RateLimiter
from app.services.analytics import (
    analyze_trend,
    format_trend_report,
    generate_ascii_chart,
    get_rate_history,
    get_top_movers,
)
from app.services.conversion import convert_amount, format_decimal, get_rate
from app.services.history import HistoryWriter
from app.services.watches import add_watch
from app.storage.models import RatesSnapshot
from app.storage.redis_store import RedisStore

logger = logging.getLogger(__name__)


def _staleness_seconds(fetched_at: str) -> int:
    fetched_dt = datetime.fromisoformat(fetched_at)
    return int((datetime.now(timezone.utc) - fetched_dt).total_seconds())


def _staleness_warning(fetched_at: str, max_staleness: int) -> str:
    staleness_seconds = _staleness_seconds(fetched_at)
    if staleness_seconds <= max_staleness:
        return ""
    return f"\n⚠️ Rates are stale ({staleness_seconds}s)."


def _format_snapshot(snapshot: RatesSnapshot) -> str:
    return f"Provider: {snapshot.provider}\nAs of: {snapshot.as_of}\nFetched: {snapshot.fetched_at}"


async def _get_snapshot(store: RedisStore, base: str) -> RatesSnapshot | None:
    return await store.get_rates_snapshot(base)


def setup_router(
    store: RedisStore,
    default_base: str,
    max_staleness_seconds: int,
    history_writer: HistoryWriter | None = None,
    rate_limiter: RateLimiter | None = None,
) -> Router:
    router = Router()

    @router.message(F.text.startswith("/help"))
    async def cmd_help(message: Message) -> None:
        await message.answer(
            "Commands:\n"
            "/rate EURUSD or /rate EUR USD\n"
            "/convert <amount> <FROM> <TO>\n"
            "/status\n"
            "/base <CURRENCY>\n"
            "/precision 2|4|6\n"
            "/watch <FROM> <TO> <target_rate|delta%>\n"
            "/watchlist\n"
            "/unwatch <id>\n"
            "/currencies\n"
            "/history <FROM> <TO> 24h|7d\n"
            "/trend EURUSD or /trend EUR USD\n"
            "/chart EUR USD [width] [height]\n"
            "/movers [limit]"
        )

    @router.message(F.text.startswith("/status"))
    async def cmd_status(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        health = await store.get_health()
        snapshot = await _get_snapshot(store, default_base)
        if not health or not snapshot:
            await message.answer("No rates available yet.")
            return
        warning = _staleness_warning(snapshot.fetched_at, max_staleness_seconds)
        error_line = f"\nLast error: {health.last_error}" if health.last_error else ""
        await message.answer(
            "Status:\n"
            f"Active provider: {health.active_provider}\n"
            f"Last success: {health.last_success_at}\n"
            f"Staleness: {_staleness_seconds(snapshot.fetched_at)}s\n"
            f"Snapshot base: {snapshot.base}"
            f"{error_line}"
            f"{warning}"
        )

    @router.message(F.text.startswith("/base"))
    async def cmd_base(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) != 2:
            await message.answer("Usage: /base <CURRENCY>")
            return
        base = parts[1].strip().upper()
        await store.set_chat_base(message.chat.id, base)
        await message.answer(f"Default base set to {base}.")

    @router.message(F.text.startswith("/precision"))
    async def cmd_precision(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        parts = message.text.split(maxsplit=1)
        precision = parse_precision_args(parts[1] if len(parts) > 1 else "")
        if precision is None:
            await message.answer("Usage: /precision 2|4|6")
            return
        await store.set_chat_precision(message.chat.id, precision)
        await message.answer(f"Precision set to {precision} decimals.")

    @router.message(F.text.startswith("/rate"))
    async def cmd_rate(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        args = message.text.removeprefix("/rate").strip()
        parsed = parse_rate_args(args)
        if not parsed:
            await message.answer("Usage: /rate EURUSD or /rate EUR USD")
            return
        from_ccy, to_ccy = parsed
        base = await store.get_chat_base(message.chat.id) or default_base
        snapshot = await _get_snapshot(store, base)
        if not snapshot:
            await message.answer("Rates not available yet.")
            return
        try:
            rate = get_rate(snapshot, from_ccy, to_ccy)
        except KeyError as exc:
            await message.answer(f"Unknown currency: {exc.args[0]}")
            return
        precision = await store.get_chat_precision(message.chat.id) or 4
        warning = _staleness_warning(snapshot.fetched_at, max_staleness_seconds)
        await message.answer(
            f"{from_ccy}/{to_ccy}: {format_decimal(rate, precision)}\n"
            f"{_format_snapshot(snapshot)}"
            f"{warning}"
        )

    @router.message(F.text.startswith("/convert"))
    async def cmd_convert(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        args = message.text.removeprefix("/convert").strip()
        parsed = parse_convert_args(args)
        if not parsed:
            await message.answer("Usage: /convert <amount> <FROM> <TO>")
            return
        amount, from_ccy, to_ccy = parsed
        base = await store.get_chat_base(message.chat.id) or default_base
        snapshot = await _get_snapshot(store, base)
        if not snapshot:
            await message.answer("Rates not available yet.")
            return
        try:
            result = convert_amount(snapshot, amount, from_ccy, to_ccy)
        except KeyError as exc:
            await message.answer(f"Unknown currency: {exc.args[0]}")
            return
        precision = await store.get_chat_precision(message.chat.id) or 4
        warning = _staleness_warning(snapshot.fetched_at, max_staleness_seconds)
        await message.answer(
            f"{format_decimal(result.amount, precision)} {from_ccy} = "
            f"{format_decimal(result.converted, precision)} {to_ccy}\n"
            f"Rate: {format_decimal(result.rate, precision)}\n"
            f"{_format_snapshot(snapshot)}"
            f"{warning}"
        )

    @router.message(F.text.startswith("/watchlist"))
    async def cmd_watchlist(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        watches = await store.list_watches(message.chat.id)
        if not watches:
            await message.answer("No active watches.")
            return
        lines = [
            f"{watch['id']}: {watch['from_ccy']}/{watch['to_ccy']} {watch['target']}"
            for watch in watches
        ]
        await message.answer("Active watches:\n" + "\n".join(lines))

    @router.message(F.text.startswith("/currencies"))
    async def cmd_currencies(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        base = await store.get_chat_base(message.chat.id) or default_base
        snapshot = await _get_snapshot(store, base)
        if not snapshot:
            await message.answer("Currencies are not available yet.")
            return
        currencies = await store.get_currencies(base)
        if not currencies:
            currencies = sorted({snapshot.base, *snapshot.rates.keys()})
        warning = _staleness_warning(snapshot.fetched_at, max_staleness_seconds)
        await message.answer(
            f"Available currencies for {base}:\n"
            + ", ".join(currencies)
            + f"\n{_format_snapshot(snapshot)}"
            + warning
        )

    @router.message(F.text.startswith("/unwatch"))
    async def cmd_unwatch(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) != 2:
            await message.answer("Usage: /unwatch <id>")
            return
        removed = await store.remove_watch(message.chat.id, parts[1].strip())
        await message.answer("Removed watch." if removed else "Watch id not found.")

    @router.message(F.text.startswith("/watch"))
    async def cmd_watch(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        args = message.text.removeprefix("/watch").strip()
        parsed = parse_watch_args(args)
        if not parsed:
            await message.answer("Usage: /watch <FROM> <TO> <target_rate|delta%>")
            return
        from_ccy, to_ccy, target = parsed
        try:
            Decimal(target.rstrip("%"))
        except Exception:
            await message.answer("Target must be a number or percent, e.g. 1.1 or 2%.")
            return
        base = await store.get_chat_base(message.chat.id) or default_base
        snapshot = await _get_snapshot(store, base)
        if not snapshot:
            await message.answer("Rates not available yet.")
            return
        try:
            baseline_rate = get_rate(snapshot, from_ccy, to_ccy)
        except KeyError as exc:
            await message.answer(f"Unknown currency: {exc.args[0]}")
            return
        watch = await add_watch(store, message.chat.id, from_ccy, to_ccy, target, baseline_rate)
        await message.answer(
            f"Watch {watch.id} added for {from_ccy}/{to_ccy} at {target} (baseline {baseline_rate})."
        )

    @router.message(F.text.startswith("/history"))
    async def cmd_history(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        if not history_writer:
            await message.answer("History is disabled.")
            return
        args = message.text.removeprefix("/history").strip()
        parsed = parse_history_args(args)
        if not parsed:
            await message.answer("Usage: /history <FROM> <TO> 24h|7d")
            return
        from_ccy, to_ccy, window = parsed
        if window not in {"24h", "7d"}:
            await message.answer("Window must be 24h or 7d.")
            return
        rows = await history_writer.get_history(from_ccy, to_ccy, window)
        if not rows:
            await message.answer("No history available.")
            return
        lines = [f"{rate} @ {as_of}" for rate, as_of in rows]
        await message.answer(
            f"History {from_ccy}/{to_ccy} ({window}):\n" + "\n".join(lines)
        )

    @router.message(F.text.startswith("/trend"))
    async def cmd_trend(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        args = message.text.removeprefix("/trend").strip()
        parsed = parse_trend_args(args)
        if not parsed:
            await message.answer("Usage: /trend EURUSD or /trend EUR USD")
            return
        from_ccy, to_ccy = parsed
        base = await store.get_chat_base(message.chat.id) or default_base
        snapshot = await _get_snapshot(store, base)
        if not snapshot:
            await message.answer("Rates not available yet.")
            return
        try:
            current_rate = get_rate(snapshot, from_ccy, to_ccy)
        except KeyError as exc:
            await message.answer(f"Unknown currency: {exc.args[0]}")
            return
        precision = await store.get_chat_precision(message.chat.id) or 4
        trend = await analyze_trend(store, from_ccy, to_ccy, base, current_rate)
        report = format_trend_report(trend, precision)
        await message.answer(report)

    @router.message(F.text.startswith("/chart"))
    async def cmd_chart(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        args = message.text.removeprefix("/chart").strip()
        parsed = parse_chart_args(args)
        if not parsed:
            await message.answer("Usage: /chart EUR USD [width] [height]")
            return
        from_ccy, to_ccy, width, height = parsed
        base = await store.get_chat_base(message.chat.id) or default_base
        points = await get_rate_history(store, from_ccy, to_ccy, base, limit=width * 2)
        if not points:
            await message.answer("No data available for chart.")
            return
        chart = generate_ascii_chart(points, width=width, height=height)
        await message.answer(f"Chart: {from_ccy}/{to_ccy}\n\n{chart}")

    @router.message(F.text.startswith("/movers"))
    async def cmd_movers(message: Message) -> None:
        if rate_limiter and not rate_limiter.allow(message.chat.id):
            await message.answer("You're doing that too fast. Please wait a moment.")
            return
        args = message.text.removeprefix("/movers").strip()
        limit = parse_movers_args(args)
        if limit is None:
            await message.answer("Usage: /movers [limit] (1-20)")
            return
        base = await store.get_chat_base(message.chat.id) or default_base
        currencies = await store.get_currencies(base)
        if not currencies:
            snapshot = await _get_snapshot(store, base)
            if not snapshot:
                await message.answer("Currencies not available yet.")
                return
            currencies = sorted({snapshot.base, *snapshot.rates.keys()})
        movers = await get_top_movers(store, base, currencies, limit)
        if not movers:
            await message.answer("No movers data available.")
            return
        
        # Format with volatility info
        lines = []
        for i, m in enumerate(movers):
            vol_indicator = "🔴" if m.volatility > Decimal('3') else "🟡" if m.volatility > Decimal('1') else "🟢"
            lines.append(
                f"{i+1}. {m.currency}: {m.change_percent:.2f}% {m.direction} {vol_indicator} (vol: {m.volatility:.2f}%)"
            )
        await message.answer(f"Top {len(movers)} movers vs {base}:\n" + "\n".join(lines))

    return router
