from decimal import Decimal, InvalidOperation


def parse_rate_args(text: str) -> tuple[str, str] | None:
    parts = text.strip().split()
    if not parts:
        return None
    if len(parts) == 1:
        pair = parts[0].upper()
        if len(pair) != 6 or not pair.isalpha():
            return None
        return pair[:3], pair[3:]
    if len(parts) == 2:
        from_ccy, to_ccy = parts[0].upper(), parts[1].upper()
        if not from_ccy.isalpha() or not to_ccy.isalpha() or len(from_ccy) > 3 or len(to_ccy) > 3:
            return None
        return from_ccy, to_ccy
    return None


def parse_convert_args(text: str) -> tuple[Decimal, str, str] | None:
    parts = text.strip().split()
    if len(parts) != 3:
        return None
    try:
        amount = Decimal(parts[0])
        if amount <= 0:
            return None
    except InvalidOperation:
        return None
    from_ccy, to_ccy = parts[1].upper(), parts[2].upper()
    if not from_ccy.isalpha() or not to_ccy.isalpha() or len(from_ccy) > 3 or len(to_ccy) > 3:
        return None
    return amount, from_ccy, to_ccy


def parse_precision_args(text: str) -> int | None:
    text = text.strip()
    if text not in {"2", "4", "6"}:
        return None
    return int(text)


def parse_watch_args(text: str) -> tuple[str, str, str] | None:
    parts = text.strip().split()
    if len(parts) != 3:
        return None
    from_ccy, to_ccy = parts[0].upper(), parts[1].upper()
    if not from_ccy.isalpha() or not to_ccy.isalpha() or len(from_ccy) > 3 or len(to_ccy) > 3:
        return None
    target = parts[2]
    # Validate target format: number or percent
    try:
        Decimal(target.rstrip("%"))
    except Exception:
        return None
    return from_ccy, to_ccy, target


def parse_history_args(text: str) -> tuple[str, str, str] | None:
    parts = text.strip().split()
    if len(parts) != 3:
        return None
    from_ccy, to_ccy = parts[0].upper(), parts[1].upper()
    if not from_ccy.isalpha() or not to_ccy.isalpha() or len(from_ccy) > 3 or len(to_ccy) > 3:
        return None
    window = parts[2]
    if window not in {"24h", "7d"}:
        return None
    return from_ccy, to_ccy, window


def parse_trend_args(text: str) -> tuple[str, str] | None:
    """Parse arguments for /trend command."""
    parts = text.strip().split()
    if not parts:
        return None
    if len(parts) == 1:
        pair = parts[0].upper()
        if len(pair) != 6 or not pair.isalpha():
            return None
        return pair[:3], pair[3:]
    if len(parts) == 2:
        from_ccy, to_ccy = parts[0].upper(), parts[1].upper()
        if not from_ccy.isalpha() or not to_ccy.isalpha() or len(from_ccy) > 3 or len(to_ccy) > 3:
            return None
        return from_ccy, to_ccy
    return None


def parse_chart_args(text: str) -> tuple[str, str, int, int] | None:
    """Parse arguments for /chart command with optional width and height."""
    parts = text.strip().split()
    if len(parts) < 2:
        return None
    
    from_ccy, to_ccy = parts[0].upper(), parts[1].upper()
    if not from_ccy.isalpha() or not to_ccy.isalpha() or len(from_ccy) > 3 or len(to_ccy) > 3:
        return None
    
    width = 40
    height = 10
    
    if len(parts) >= 3:
        try:
            width = int(parts[2])
            if width < 10 or width > 80:
                return None
        except ValueError:
            return None
    
    if len(parts) >= 4:
        try:
            height = int(parts[3])
            if height < 5 or height > 20:
                return None
        except ValueError:
            return None
    
    return from_ccy, to_ccy, width, height


def parse_movers_args(text: str) -> int | None:
    """Parse arguments for /movers command (optional limit)."""
    parts = text.strip().split()
    if not parts:
        return 5
    
    if len(parts) == 1:
        try:
            limit = int(parts[0])
            if limit < 1 or limit > 20:
                return None
            return limit
        except ValueError:
            return None
    
    return None
