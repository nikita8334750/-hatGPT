from decimal import Decimal

from app.services.conversion import convert_amount, format_decimal, get_rate
from app.storage.redis_store import RatesSnapshot


def test_cross_rate():
    snapshot = RatesSnapshot(
        base="USD",
        rates={"EUR": Decimal("0.9"), "JPY": Decimal("110")},
        provider="test",
        as_of="2024-01-01",
        fetched_at="2024-01-01T00:00:00+00:00",
    )
    rate = get_rate(snapshot, "EUR", "JPY")
    assert rate == Decimal("110") / Decimal("0.9")
    result = convert_amount(snapshot, Decimal("10"), "EUR", "JPY")
    assert result.converted == Decimal("10") * rate


def test_format_decimal_precision():
    assert format_decimal(Decimal("1.23456"), 2) == "1.23"
    assert format_decimal(Decimal("1.23456"), 4) == "1.2346"
