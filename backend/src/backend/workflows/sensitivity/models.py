"""Contracts for transparent, one-way maximum-price sensitivities."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import require_positive, require_return_rate
from backend.workflows.underwriting import UnderwritingAssumptions


@dataclass(frozen=True, slots=True)
class SensitivityAssumptions:
    """Base underwriting and constraints shared by every scenario.

    Price bounds are optional; when omitted each scenario brackets its own
    answer from the reference purchase price exactly as the solver does.
    """

    underwriting: UnderwritingAssumptions
    target_levered_irr: Decimal
    minimum_dscr: Decimal
    minimum_purchase_price: Decimal | None = None
    maximum_purchase_price: Decimal | None = None
    price_tolerance: Decimal = Decimal("0.01")
    max_iterations: int = 100

    def __post_init__(self) -> None:
        require_return_rate("target_levered_irr", self.target_levered_irr)
        require_positive("minimum_dscr", self.minimum_dscr)
        if self.minimum_purchase_price is not None:
            require_positive("minimum_purchase_price", self.minimum_purchase_price)
        if self.maximum_purchase_price is not None:
            require_positive("maximum_purchase_price", self.maximum_purchase_price)
        require_positive("price_tolerance", self.price_tolerance)
        if (
            self.minimum_purchase_price is not None
            and self.maximum_purchase_price is not None
            and self.minimum_purchase_price >= self.maximum_purchase_price
        ):
            raise ValueError("minimum_purchase_price must be less than maximum_purchase_price")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")


@dataclass(frozen=True, slots=True)
class SensitivityPoint:
    label: str
    value: Decimal | None
    maximum_purchase_price: Decimal | None
    error: str | None


@dataclass(frozen=True, slots=True)
class SensitivityDimension:
    key: str
    label: str
    unit: str
    points: tuple[SensitivityPoint, ...]
    description: str | None = None


@dataclass(frozen=True, slots=True)
class SensitivityResult:
    dimensions: tuple[SensitivityDimension, ...]
