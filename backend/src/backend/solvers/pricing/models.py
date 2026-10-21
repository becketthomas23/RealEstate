"""Contracts for the target-return maximum-price solver."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import ZERO, require_positive, require_return_rate
from backend.workflows.underwriting import UnderwritingAssumptions, UnderwritingResult


@dataclass(frozen=True, slots=True)
class MaximumPriceAssumptions:
    underwriting: UnderwritingAssumptions
    target_levered_irr: Decimal
    minimum_dscr: Decimal
    minimum_purchase_price: Decimal
    maximum_purchase_price: Decimal
    price_tolerance: Decimal = Decimal("0.01")
    max_iterations: int = 100

    def __post_init__(self) -> None:
        require_return_rate("target_levered_irr", self.target_levered_irr)
        require_positive("minimum_dscr", self.minimum_dscr)
        require_positive("minimum_purchase_price", self.minimum_purchase_price)
        require_positive("maximum_purchase_price", self.maximum_purchase_price)
        require_positive("price_tolerance", self.price_tolerance)
        if self.minimum_purchase_price >= self.maximum_purchase_price:
            raise ValueError("minimum_purchase_price must be less than maximum_purchase_price")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")


@dataclass(frozen=True, slots=True)
class MaximumPriceResult:
    maximum_purchase_price: Decimal
    recommended_bid_floor: Decimal
    recommended_bid_ceiling: Decimal
    underwriting: UnderwritingResult
    iterations: int
