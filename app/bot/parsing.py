from decimal import Decimal, InvalidOperation


def parse_rate_args(text: str) -> tuple[str, str] | None:
    parts = text.strip().split()
    if not parts:
        return None
    if len(parts) == 1:
        pair = parts[0].upper()
        if len(pair) != 6:
            return None
        return pair[:3], pair[3:]
    if len(parts) == 2:
        return parts[0].upper(), parts[1].upper()
    return None


def parse_convert_args(text: str) -> tuple[Decimal, str, str] | None:
    parts = text.strip().split()
    if len(parts) != 3:
        return None
    try:
        amount = Decimal(parts[0])
    except InvalidOperation:
        return None
    return amount, parts[1].upper(), parts[2].upper()


def parse_precision_args(text: str) -> int | None:
    text = text.strip()
    if text not in {"2", "4", "6"}:
        return None
    return int(text)


def parse_watch_args(text: str) -> tuple[str, str, str] | None:
    parts = text.strip().split()
    if len(parts) != 3:
        return None
    return parts[0].upper(), parts[1].upper(), parts[2]


def parse_history_args(text: str) -> tuple[str, str, str] | None:
    parts = text.strip().split()
    if len(parts) != 3:
        return None
    return parts[0].upper(), parts[1].upper(), parts[2]
