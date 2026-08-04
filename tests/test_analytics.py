"""Tests for the new analytics functionality."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from app.services.analytics import (
    RatePoint,
    TrendAnalysis,
    TopMover,
    analyze_trend,
    generate_ascii_chart,
    format_trend_report,
    get_rate_history,
    get_top_movers,
)
from app.bot.parsing import (
    parse_trend_args,
    parse_chart_args,
    parse_movers_args,
)


class TestParseTrendArgs:
    """Test parsing of /trend command arguments."""

    def test_pair_format(self):
        """Test EURUSD pair format."""
        result = parse_trend_args("EURUSD")
        assert result == ("EUR", "USD")

    def test_separate_currencies(self):
        """Test separate EUR USD format."""
        result = parse_trend_args("EUR USD")
        assert result == ("EUR", "USD")

    def test_lowercase_input(self):
        """Test lowercase input is converted to uppercase."""
        result = parse_trend_args("eurusd")
        assert result == ("EUR", "USD")

    def test_invalid_pair_length(self):
        """Test invalid pair length is rejected."""
        result = parse_trend_args("EURUS")
        assert result is None

    def test_no_args(self):
        """Test empty input is rejected."""
        result = parse_trend_args("")
        assert result is None

    def test_too_many_args(self):
        """Test too many arguments are rejected."""
        result = parse_trend_args("EUR USD GBP")
        assert result is None


class TestParseChartArgs:
    """Test parsing of /chart command arguments."""

    def test_minimal_args(self):
        """Test minimal EUR USD format."""
        result = parse_chart_args("EUR USD")
        assert result == ("EUR", "USD", 40, 10)

    def test_with_width(self):
        """Test with custom width."""
        result = parse_chart_args("EUR USD 60")
        assert result == ("EUR", "USD", 60, 10)

    def test_with_width_and_height(self):
        """Test with custom width and height."""
        result = parse_chart_args("EUR USD 50 15")
        assert result == ("EUR", "USD", 50, 15)

    def test_width_too_small(self):
        """Test width below minimum is rejected."""
        result = parse_chart_args("EUR USD 5")
        assert result is None

    def test_width_too_large(self):
        """Test width above maximum is rejected."""
        result = parse_chart_args("EUR USD 100")
        assert result is None

    def test_height_too_small(self):
        """Test height below minimum is rejected."""
        result = parse_chart_args("EUR USD 40 3")
        assert result is None

    def test_height_too_large(self):
        """Test height above maximum is rejected."""
        result = parse_chart_args("EUR USD 40 25")
        assert result is None


class TestParseMoversArgs:
    """Test parsing of /movers command arguments."""

    def test_default_limit(self):
        """Test default limit when no args."""
        result = parse_movers_args("")
        assert result == 5

    def test_custom_limit(self):
        """Test custom limit."""
        result = parse_movers_args("10")
        assert result == 10

    def test_limit_too_small(self):
        """Test limit below minimum is rejected."""
        result = parse_movers_args("0")
        assert result is None

    def test_limit_too_large(self):
        """Test limit above maximum is rejected."""
        result = parse_movers_args("25")
        assert result is None


class TestGenerateAsciiChart:
    """Test ASCII chart generation."""

    def test_empty_points(self):
        """Test empty points list."""
        result = generate_ascii_chart([])
        assert "No data" in result

    def test_single_point(self):
        """Test single point returns stable message."""
        points = [RatePoint(timestamp=datetime.now(timezone.utc), rate=Decimal('1.1'))]
        result = generate_ascii_chart(points)
        assert "stable" in result

    def test_multiple_points(self):
        """Test multiple points generates chart."""
        now = datetime.now(timezone.utc)
        points = [
            RatePoint(timestamp=now - timedelta(hours=i), rate=Decimal(str(1.1 + i * 0.01)))
            for i in range(10)
        ]
        result = generate_ascii_chart(points, width=20, height=5)
        assert "Max:" in result
        assert "Min:" in result
        assert "█" in result

    def test_chart_dimensions(self):
        """Test chart respects dimensions."""
        now = datetime.now(timezone.utc)
        points = [
            RatePoint(timestamp=now - timedelta(hours=i), rate=Decimal(str(1.0 + i * 0.01)))
            for i in range(20)
        ]
        result = generate_ascii_chart(points, width=30, height=8)
        lines = result.split('\n')
        # Check that chart has appropriate height
        assert len(lines) >= 8


class TestFormatTrendReport:
    """Test trend report formatting."""

    def test_upward_trend(self):
        """Test upward trend formatting."""
        trend = TrendAnalysis(
            from_ccy="EUR",
            to_ccy="USD",
            current_rate=Decimal('1.1'),
            min_rate=Decimal('1.05'),
            max_rate=Decimal('1.1'),
            avg_rate=Decimal('1.075'),
            change_percent=Decimal('5.0'),
            trend="up",
            points=[]
        )
        report = format_trend_report(trend)
        assert "📈" in report
        assert "UP" in report
        assert "+5.0000%" in report

    def test_downward_trend(self):
        """Test downward trend formatting."""
        trend = TrendAnalysis(
            from_ccy="EUR",
            to_ccy="USD",
            current_rate=Decimal('1.05'),
            min_rate=Decimal('1.05'),
            max_rate=Decimal('1.1'),
            avg_rate=Decimal('1.075'),
            change_percent=Decimal('-5.0'),
            trend="down",
            points=[]
        )
        report = format_trend_report(trend)
        assert "📉" in report
        assert "DOWN" in report
        assert "-5.0000%" in report

    def test_stable_trend(self):
        """Test stable trend formatting."""
        trend = TrendAnalysis(
            from_ccy="EUR",
            to_ccy="USD",
            current_rate=Decimal('1.08'),
            min_rate=Decimal('1.07'),
            max_rate=Decimal('1.09'),
            avg_rate=Decimal('1.08'),
            change_percent=Decimal('0.5'),
            trend="stable",
            points=[]
        )
        report = format_trend_report(trend)
        assert "➡️" in report
        assert "STABLE" in report

    def test_custom_precision(self):
        """Test custom precision formatting."""
        trend = TrendAnalysis(
            from_ccy="EUR",
            to_ccy="USD",
            current_rate=Decimal('1.08123456'),
            min_rate=Decimal('1.07'),
            max_rate=Decimal('1.09'),
            avg_rate=Decimal('1.08'),
            change_percent=Decimal('0.5'),
            trend="stable",
            points=[]
        )
        report = format_trend_report(trend, precision=2)
        assert "1.08" in report


@pytest.mark.asyncio
async def test_analyze_trend_no_history():
    """Test trend analysis with no historical data."""
    import fakeredis.aioredis
    from app.storage.redis_store import RedisStore
    
    redis = fakeredis.aioredis.FakeRedis()
    store = RedisStore(redis)
    
    result = await analyze_trend(
        store,
        "EUR",
        "USD",
        "USD",
        Decimal('1.1'),
        limit=24
    )
    
    assert result.from_ccy == "EUR"
    assert result.to_ccy == "USD"
    assert result.current_rate == Decimal('1.1')
    assert result.trend == "stable"
    assert result.change_percent == Decimal('0')
    assert len(result.points) == 0


@pytest.mark.asyncio
async def test_get_top_movers_empty():
    """Test top movers with no data."""
    import fakeredis.aioredis
    from app.storage.redis_store import RedisStore
    
    redis = fakeredis.aioredis.FakeRedis()
    store = RedisStore(redis)
    
    result = await get_top_movers(store, "USD", ["EUR", "GBP", "JPY"], limit=5)
    assert result == []
