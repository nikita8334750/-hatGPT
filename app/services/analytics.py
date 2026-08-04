"""Analytics service for currency trends and chart generation."""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Deque

from app.storage.redis_store import RedisStore

logger = logging.getLogger(__name__)


@dataclass
class RatePoint:
    """Single rate measurement point."""
    timestamp: datetime
    rate: Decimal


@dataclass
class TrendAnalysis:
    """Result of trend analysis for a currency pair."""
    from_ccy: str
    to_ccy: str
    current_rate: Decimal
    min_rate: Decimal
    max_rate: Decimal
    avg_rate: Decimal
    change_percent: Decimal
    trend: str  # "up", "down", "stable"
    volatility: Decimal = field(default_factory=lambda: Decimal('0'))
    points: list[RatePoint] = field(default_factory=list)


@dataclass
class TopMover:
    """Top moving currency information."""
    currency: str
    change_percent: Decimal
    direction: str  # "up", "down"
    volatility: Decimal = field(default_factory=lambda: Decimal('0'))


def _parse_timestamp(ts_str: str) -> datetime:
    """Parse ISO format timestamp."""
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        logger.warning(f"Failed to parse timestamp: {ts_str}")
        return datetime.now(timezone.utc)


async def get_rate_history(
    store: RedisStore,
    from_ccy: str,
    to_ccy: str,
    base: str,
    limit: int = 24
) -> list[RatePoint]:
    """
    Retrieve historical rate points from Redis.
    
    Args:
        store: Redis storage instance
        from_ccy: Source currency code
        to_ccy: Target currency code
        base: Base currency for rates
        limit: Maximum number of points to retrieve
    
    Returns:
        List of RatePoint objects sorted by timestamp
    """
    history_key = f"history:{base}:{from_ccy}:{to_ccy}"
    
    try:
        raw_data = await store.redis.lrange(history_key, 0, limit - 1)
        if not raw_data:
            return []
        
        points = []
        for item in raw_data:
            try:
                data = item.decode('utf-8')
                parts = data.split('|')
                if len(parts) >= 2:
                    ts = _parse_timestamp(parts[0])
                    rate = Decimal(parts[1])
                    points.append(RatePoint(timestamp=ts, rate=rate))
            except (UnicodeDecodeError, InvalidOperation, IndexError) as e:
                logger.debug(f"Skipping malformed history entry: {e}")
                continue
        
        return sorted(points, key=lambda p: p.timestamp)
    except Exception as e:
        logger.warning(f"Failed to retrieve history for {from_ccy}/{to_ccy}: {e}")
        return []


async def analyze_trend(
    store: RedisStore,
    from_ccy: str,
    to_ccy: str,
    base: str,
    current_rate: Decimal,
    limit: int = 24
) -> TrendAnalysis:
    """
    Analyze trend for a currency pair with volatility calculation.
    
    Args:
        store: Redis storage instance
        from_ccy: Source currency code
        to_ccy: Target currency code
        base: Base currency for rates
        current_rate: Current exchange rate
        limit: Number of historical points to analyze
    
    Returns:
        TrendAnalysis object with trend information including volatility
    """
    points = await get_rate_history(store, from_ccy, to_ccy, base, limit)
    
    if not points:
        return TrendAnalysis(
            from_ccy=from_ccy,
            to_ccy=to_ccy,
            current_rate=current_rate,
            min_rate=current_rate,
            max_rate=current_rate,
            avg_rate=current_rate,
            change_percent=Decimal('0'),
            trend="stable",
            volatility=Decimal('0'),
            points=[]
        )
    
    rates = [p.rate for p in points]
    min_rate = min(rates)
    max_rate = max(rates)
    avg_rate = sum(rates) / len(rates)
    
    # Calculate volatility (standard deviation of returns)
    if len(rates) > 1:
        returns = []
        for i in range(1, len(rates)):
            if rates[i-1] != 0:
                ret = (rates[i] - rates[i-1]) / rates[i-1]
                returns.append(ret)
        
        if returns:
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            volatility = abs(variance.sqrt()) * 100  # As percentage
        else:
            volatility = Decimal('0')
    else:
        volatility = Decimal('0')
    
    oldest_rate = points[0].rate if points else current_rate
    if oldest_rate != 0:
        change_percent = ((current_rate - oldest_rate) / oldest_rate) * 100
    else:
        change_percent = Decimal('0')
    
    # Determine trend with volatility consideration
    if volatility < Decimal('0.5'):
        trend = "stable"
    elif change_percent > Decimal('1'):
        trend = "up"
    elif change_percent < Decimal('-1'):
        trend = "down"
    else:
        trend = "stable"
    
    return TrendAnalysis(
        from_ccy=from_ccy,
        to_ccy=to_ccy,
        current_rate=current_rate,
        min_rate=min_rate,
        max_rate=max_rate,
        avg_rate=avg_rate,
        change_percent=change_percent,
        trend=trend,
        volatility=volatility,
        points=points
    )


def generate_ascii_chart(
    points: list[RatePoint],
    width: int = 40,
    height: int = 10
) -> str:
    """
    Generate ASCII chart from rate points with improved formatting.
    
    Args:
        points: List of RatePoint objects
        width: Chart width in characters (10-80)
        height: Chart height in lines (5-20)
    
    Returns:
        ASCII art chart as string with enhanced formatting
    """
    # Validate and clamp dimensions
    width = max(10, min(80, width))
    height = max(5, min(20, height))
    
    if not points:
        return "No data available for chart."
    
    rates = [p.rate for p in points]
    min_rate = min(rates)
    max_rate = max(rates)
    
    if min_rate == max_rate:
        return f"Rate stable at {min_rate:.6f}"
    
    range_rate = max_rate - min_rate
    
    # Add padding to avoid edge clipping
    padding = range_rate * Decimal('0.05')  # 5% padding
    min_rate_padded = min_rate - padding
    max_rate_padded = max_rate + padding
    range_padded = max_rate_padded - min_rate_padded
    
    lines: Deque[str] = deque()
    
    for row in range(height, 0, -1):
        threshold = min_rate_padded + (range_padded * Decimal(row) / Decimal(height))
        line_chars = []
        
        # Sample points if we have more than width
        step = max(1, len(points) // width)
        sampled_points = points[::step][:width]
        
        for point in sampled_points:
            if point.rate >= threshold:
                line_chars.append('█')
            else:
                line_chars.append(' ')
        
        # Pad or truncate to exact width
        compressed = ''.join(line_chars).ljust(width)[:width]
        lines.appendleft(compressed)
    
    chart_lines = list(lines)
    
    # Format labels with proper precision
    min_label = f"Min: {min_rate:.6f}"
    max_label = f"Max: {max_rate:.6f}"
    
    result = [max_label]
    result.extend(chart_lines)
    result.append(min_label)
    
    # Calculate time range
    time_range = ""
    if len(points) >= 2:
        oldest = points[0].timestamp
        newest = points[-1].timestamp
        hours = (newest - oldest).total_seconds() / 3600
        if hours >= 24:
            time_range = f"Period: {hours/24:.1f} days ({len(points)} points)"
        elif hours >= 1:
            time_range = f"Period: {hours:.1f} hours ({len(points)} points)"
        else:
            minutes = hours * 60
            time_range = f"Period: {minutes:.0f} minutes ({len(points)} points)"
    
    if time_range:
        result.append(time_range)
    
    return '\n'.join(result)


async def get_top_movers(
    store: RedisStore,
    base: str,
    currencies: list[str],
    limit: int = 5
) -> list[TopMover]:
    """
    Get top moving currencies against base with volatility analysis.
    
    Args:
        store: Redis storage instance
        base: Base currency
        currencies: List of currencies to analyze
        limit: Number of top movers to return
    
    Returns:
        List of TopMover objects sorted by absolute change with volatility info
    """
    movers = []
    
    for currency in currencies:
        if currency == base:
            continue
        
        try:
            snapshot = await store.get_rates_snapshot(base)
            if not snapshot:
                continue
            
            current_rate = snapshot.rates.get(currency)
            if not current_rate:
                continue
            
            points = await get_rate_history(store, base, currency, base, limit=24)
            
            if points and points[0].rate != 0:
                oldest_rate = points[0].rate
                change_percent = ((current_rate - oldest_rate) / oldest_rate) * 100
                
                # Calculate volatility
                if len(points) > 1:
                    rates = [p.rate for p in points]
                    returns = []
                    for i in range(1, len(rates)):
                        if rates[i-1] != 0:
                            ret = (rates[i] - rates[i-1]) / rates[i-1]
                            returns.append(ret)
                    
                    if returns:
                        avg_return = sum(returns) / len(returns)
                        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                        volatility = abs(variance.sqrt()) * 100
                    else:
                        volatility = Decimal('0')
                else:
                    volatility = Decimal('0')
                
                direction = "up" if change_percent > 0 else "down"
                
                movers.append(TopMover(
                    currency=currency,
                    change_percent=abs(change_percent),
                    direction=direction,
                    volatility=volatility
                ))
        except Exception as e:
            logger.warning(f"Failed to analyze {currency}: {e}")
            continue
    
    movers.sort(key=lambda m: m.change_percent, reverse=True)
    return movers[:limit]


def format_trend_report(trend: TrendAnalysis, precision: int = 4) -> str:
    """
    Format trend analysis as human-readable report with volatility.
    
    Args:
        trend: TrendAnalysis object
        precision: Decimal precision for formatting
    
    Returns:
        Formatted report string including volatility info
    """
    trend_icon = {"up": "📈", "down": "📉", "stable": "➡️"}
    
    # Add volatility indicator
    if trend.volatility < Decimal('1'):
        vol_label = "Low"
        vol_icon = "🟢"
    elif trend.volatility < Decimal('3'):
        vol_label = "Medium"
        vol_icon = "🟡"
    else:
        vol_label = "High"
        vol_icon = "🔴"
    
    report = [
        f"Trend Analysis: {trend.from_ccy}/{trend.to_ccy}",
        f"Current Rate: {trend.current_rate:.{precision}f}",
        f"Min: {trend.min_rate:.{precision}f}",
        f"Max: {trend.max_rate:.{precision}f}",
        f"Avg: {trend.avg_rate:.{precision}f}",
        f"Change: {trend.change_percent:+.{precision}f}%",
        f"Volatility: {vol_icon} {vol_label} ({trend.volatility:.{precision}f}%)",
        f"Trend: {trend_icon.get(trend.trend, '❓')} {trend.trend.upper()}"
    ]
    
    return '\n'.join(report)
