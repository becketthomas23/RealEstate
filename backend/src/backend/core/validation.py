"""Small validation helpers shared by financial-domain models."""

from decimal import Decimal


ZERO = Decimal("0")
ONE = Decimal("1")


def require_positive(name: str, value: Decimal) -> None:
    if value <= ZERO:
        raise ValueError(f"{name} must be greater than zero")


def require_non_negative(name: str, value: Decimal) -> None:
    if value < ZERO:
        raise ValueError(f"{name} must be non-negative")


def require_rate(name: str, value: Decimal, *, allow_negative: bool = False) -> None:
    lower_bound = Decimal("-1") if allow_negative else ZERO
    if not lower_bound <= value < ONE:
        bounds = "between -1 (inclusive) and 1 (exclusive)" if allow_negative else "between 0 (inclusive) and 1 (exclusive)"
        raise ValueError(f"{name} must be {bounds}")
