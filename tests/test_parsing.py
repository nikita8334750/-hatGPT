from decimal import Decimal

from app.bot.parsing import parse_convert_args, parse_rate_args


def test_parse_rate_pair():
    assert parse_rate_args("EURUSD") == ("EUR", "USD")
    assert parse_rate_args("eur usd") == ("EUR", "USD")


def test_parse_convert_args():
    result = parse_convert_args("100 usd eur")
    assert result == (Decimal("100"), "USD", "EUR")
