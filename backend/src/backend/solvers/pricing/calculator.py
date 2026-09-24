"""Bounded binary-search solver for maximum acceptable purchase price."""

from dataclasses import replace
from decimal import Decimal

from backend.workflows.underwriting import calculate_underwriting

from .models import MaximumPriceAssumptions, MaximumPriceResult


def solve_maximum_purchase_price(assumptions: MaximumPriceAssumptions) -> MaximumPriceResult:
    """Find the highest price satisfying the IRR and minimum-DSCR constraints.

    The caller supplies a price range that brackets the solution: the lower
    endpoint must be feasible and the upper endpoint must be infeasible. This
    prevents returning a misleading result when a search range is too narrow.
    """
    low = assumptions.minimum_purchase_price
    high = assumptions.maximum_purchase_price
    low_result = _underwrite_at_price(assumptions, low)
    if not _meets_constraints(assumptions, low_result):
        raise ValueError("minimum_purchase_price does not satisfy the return and coverage constraints")
    if _meets_constraints(assumptions, _underwrite_at_price(assumptions, high)):
        raise ValueError("maximum_purchase_price still satisfies constraints; provide a higher bound")

    for iteration in range(1, assumptions.max_iterations + 1):
        if high - low <= assumptions.price_tolerance:
            return MaximumPriceResult(low, low_result, iteration - 1)
        midpoint = (low + high) / Decimal("2")
        midpoint_result = _underwrite_at_price(assumptions, midpoint)
        if _meets_constraints(assumptions, midpoint_result):
            low, low_result = midpoint, midpoint_result
        else:
            high = midpoint
    raise ValueError("maximum-price solver did not converge within max_iterations")


def _underwrite_at_price(assumptions: MaximumPriceAssumptions, purchase_price: Decimal):
    return calculate_underwriting(replace(assumptions.underwriting, purchase_price=purchase_price))


def _meets_constraints(assumptions: MaximumPriceAssumptions, result) -> bool:
    return result.returns.levered_irr >= assumptions.target_levered_irr and result.returns.minimum_dscr >= assumptions.minimum_dscr
