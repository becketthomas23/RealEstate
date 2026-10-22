"""Contracts for the target-return maximum-price solver."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import require_positive, require_return_rate
from backend.workflows.underwriting import UnderwritingAssumptions, UnderwritingResult


@dataclass(frozen=True, slots=True)
class MaximumPriceAssumptions:
    """Return and coverage constraints plus an optional explicit price bracket.

    When either bound is omitted the solver brackets the answer itself,
    starting from the reference purchase price in ``underwriting``. Supplying
    both bounds keeps the original strict behaviour: the lower bound must be
    feasible and the upper bound infeasible.
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

    @property
    def has_explicit_bracket(self) -> bool:
        return self.minimum_purchase_price is not None and self.maximum_purchase_price is not None


@dataclass(frozen=True, slots=True)
class MaximumPriceResult:
    maximum_purchase_price: Decimal
    recommended_bid_floor: Decimal
    recommended_bid_ceiling: Decimal
    underwriting: UnderwritingResult
    iterations: int
    binding_constraint: str
    searched_minimum_price: Decimal
    searched_maximum_price: Decimal
