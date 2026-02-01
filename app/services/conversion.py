from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.storage.redis_store import RatesSnapshot


@dataclass(frozen=True)
class ConversionResult:
    amount: Decimal
    rate: Decimal
    converted: Decimal


def get_rate(snapshot: RatesSnapshot, from_ccy: str, to_ccy: str) -> Decimal:
    from_ccy = from_ccy.upper()
    to_ccy = to_ccy.upper()
    if from_ccy == to_ccy:
        return Decimal("1")
    base = snapshot.base.upper()
    rates = snapshot.rates

    if base == from_ccy:
        if to_ccy not in rates:
            raise KeyError(to_ccy)
        return rates[to_ccy]
    if base == to_ccy:
        if from_ccy not in rates:
            raise KeyError(from_ccy)
        return Decimal("1") / rates[from_ccy]

    if from_ccy not in rates or to_ccy not in rates:
        missing = from_ccy if from_ccy not in rates else to_ccy
        raise KeyError(missing)
    return rates[to_ccy] / rates[from_ccy]


def convert_amount(
    snapshot: RatesSnapshot,
    amount: Decimal,
    from_ccy: str,
    to_ccy: str,
) -> ConversionResult:
    rate = get_rate(snapshot, from_ccy, to_ccy)
    converted = amount * rate
    return ConversionResult(amount=amount, rate=rate, converted=converted)


def format_decimal(value: Decimal, precision: int) -> str:
    quantizer = Decimal("1").scaleb(-precision)
    return str(value.quantize(quantizer, rounding=ROUND_HALF_UP))
