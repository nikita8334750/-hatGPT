from decimal import Decimal

import pytest

from app.bot.parsing import parse_convert_args, parse_rate_args, parse_watch_args, parse_history_args


def test_parse_rate_pair():
    assert parse_rate_args("EURUSD") == ("EUR", "USD")
    assert parse_rate_args("eur usd") == ("EUR", "USD")


def test_parse_convert_args():
    result = parse_convert_args("100 usd eur")
    assert result == (Decimal("100"), "USD", "EUR")


def test_parse_rate_rejects_invalid_input():
    # Non-alphabetic characters
    assert parse_rate_args("EU1USD") is None
    assert parse_rate_args("EUR@USD") is None
    # Wrong length
    assert parse_rate_args("EUSD") is None
    assert parse_rate_args("EURRUSD") is None
    # Too long currency codes
    assert parse_rate_args("EURR USDD") is None


def test_parse_convert_rejects_invalid_input():
    # Negative amount
    assert parse_convert_args("-100 USD EUR") is None
    # Zero amount
    assert parse_convert_args("0 USD EUR") is None
    # Invalid currency codes
    assert parse_convert_args("100 EU1 USD") is None
    assert parse_convert_args("100 USD EURR") is None
    # Non-alphabetic
    assert parse_convert_args("100 EU@ USD") is None


def test_parse_watch_args_validation():
    # Valid cases
    assert parse_watch_args("EUR USD 1.2") == ("EUR", "USD", "1.2")
    assert parse_watch_args("EUR USD 5%") == ("EUR", "USD", "5%")
    # Invalid currency codes
    assert parse_watch_args("EU1 USD 1.2") is None
    assert parse_watch_args("EUR USDD 1.2") is None
    # Invalid target format
    assert parse_watch_args("EUR USD abc") is None


def test_parse_history_args_validation():
    # Valid cases
    assert parse_history_args("EUR USD 24h") == ("EUR", "USD", "24h")
    assert parse_history_args("EUR USD 7d") == ("EUR", "USD", "7d")
    # Invalid window
    assert parse_history_args("EUR USD 1h") is None
    assert parse_history_args("EUR USD 30d") is None
    # Invalid currency codes
    assert parse_history_args("EU1 USD 24h") is None
