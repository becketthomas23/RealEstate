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


def require_return_rate(name: str, value: Decimal) -> None:
    """Require an economically valid return hurdle without imposing a ceiling.

    A return cannot be -100% or less because it would make the IRR discount
    factor undefined or negative. Unlike an input rate such as vacancy or LTV,
    however, a levered-return target can exceed 100% in a high-risk or
    development case.
    """
    if value <= Decimal("-1"):
        raise ValueError(f"{name} must be greater than -1")
