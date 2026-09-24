"""Contracts for transparent, one-way maximum-price sensitivities."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import require_positive, require_rate
from backend.workflows.underwriting import UnderwritingAssumptions


@dataclass(frozen=True, slots=True)
class SensitivityAssumptions:
    """Base underwriting and constraints shared by every scenario."""

    underwriting: UnderwritingAssumptions
    target_levered_irr: Decimal
    minimum_dscr: Decimal
    minimum_purchase_price: Decimal
    maximum_purchase_price: Decimal
    price_tolerance: Decimal = Decimal("0.01")
    max_iterations: int = 100

    def __post_init__(self) -> None:
        require_rate("target_levered_irr", self.target_levered_irr, allow_negative=True)
        require_positive("minimum_dscr", self.minimum_dscr)
        require_positive("minimum_purchase_price", self.minimum_purchase_price)
        require_positive("maximum_purchase_price", self.maximum_purchase_price)
        require_positive("price_tolerance", self.price_tolerance)
        if self.minimum_purchase_price >= self.maximum_purchase_price:
            raise ValueError("minimum_purchase_price must be less than maximum_purchase_price")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")


@dataclass(frozen=True, slots=True)
class SensitivityPoint:
    label: str
    value: Decimal
    maximum_purchase_price: Decimal | None
    error: str | None


@dataclass(frozen=True, slots=True)
class SensitivityDimension:
    key: str
    label: str
    unit: str
    points: tuple[SensitivityPoint, ...]


@dataclass(frozen=True, slots=True)
class SensitivityResult:
    dimensions: tuple[SensitivityDimension, ...]
