"""Bounded binary-search solver for maximum acceptable purchase price."""

from dataclasses import replace
from decimal import Decimal

from backend.workflows.underwriting import calculate_underwriting

from .models import MaximumPriceAssumptions, MaximumPriceResult


RECOMMENDED_BID_DISCOUNT = Decimal("0.05")
BRACKET_EXPANSIONS = 40
TWO = Decimal("2")


def solve_maximum_purchase_price(assumptions: MaximumPriceAssumptions) -> MaximumPriceResult:
    """Find the highest price satisfying the IRR and minimum-DSCR constraints.

    Both constraints loosen as the price falls, so the feasible region is a
    single interval below the answer. With an explicit bracket the lower bound
    must be feasible and the upper bound infeasible; otherwise the solver
    doubles or halves the reference price until it finds such a bracket.
    """
    low, high = _bracket(assumptions)
    searched_minimum_price, searched_maximum_price = low, high
    low_result = _underwrite_at_price(assumptions, low)

    for iteration in range(1, assumptions.max_iterations + 1):
        if high - low <= assumptions.price_tolerance:
            return MaximumPriceResult(
                maximum_purchase_price=low,
                recommended_bid_floor=low * (Decimal("1") - RECOMMENDED_BID_DISCOUNT),
                recommended_bid_ceiling=low,
                underwriting=low_result,
                iterations=iteration - 1,
                binding_constraint=_binding_constraint(assumptions, low_result),
                searched_minimum_price=searched_minimum_price,
                searched_maximum_price=searched_maximum_price,
            )
        midpoint = (low + high) / TWO
        midpoint_result = _underwrite_at_price(assumptions, midpoint)
        if _meets_constraints(assumptions, midpoint_result):
            low, low_result = midpoint, midpoint_result
        else:
            high = midpoint
    raise ValueError("maximum-price solver did not converge within max_iterations")


def _bracket(assumptions: MaximumPriceAssumptions) -> tuple[Decimal, Decimal]:
    if assumptions.has_explicit_bracket:
        low, high = assumptions.minimum_purchase_price, assumptions.maximum_purchase_price
        if not _meets_constraints(assumptions, _underwrite_at_price(assumptions, low)):
            raise ValueError("minimum_purchase_price does not satisfy the return and coverage constraints")
        if _meets_constraints(assumptions, _underwrite_at_price(assumptions, high)):
            raise ValueError("maximum_purchase_price still satisfies constraints; provide a higher bound")
        return low, high

    start = assumptions.underwriting.purchase_price
    if _meets_constraints(assumptions, _underwrite_at_price(assumptions, start)):
        low = assumptions.minimum_purchase_price if assumptions.minimum_purchase_price is not None else start
        high = start
        for _ in range(BRACKET_EXPANSIONS):
            high *= TWO
            if assumptions.maximum_purchase_price is not None and high >= assumptions.maximum_purchase_price:
                high = assumptions.maximum_purchase_price
                if _meets_constraints(assumptions, _underwrite_at_price(assumptions, high)):
                    raise ValueError("maximum_purchase_price still satisfies constraints; provide a higher bound")
                return low, high
            if not _meets_constraints(assumptions, _underwrite_at_price(assumptions, high)):
                return low, high
        raise ValueError("the return and coverage constraints are satisfied at every searched price; raise the target return")

    high = assumptions.maximum_purchase_price if assumptions.maximum_purchase_price is not None else start
    low = start
    for _ in range(BRACKET_EXPANSIONS):
        low /= TWO
        if assumptions.minimum_purchase_price is not None and low <= assumptions.minimum_purchase_price:
            low = assumptions.minimum_purchase_price
            if not _meets_constraints(assumptions, _underwrite_at_price(assumptions, low)):
                raise ValueError("minimum_purchase_price does not satisfy the return and coverage constraints")
            return low, high
        if _meets_constraints(assumptions, _underwrite_at_price(assumptions, low)):
            return low, high
    raise ValueError("no purchase price satisfies the return and coverage constraints; review the target return, DSCR floor, or operating assumptions")


def _underwrite_at_price(assumptions: MaximumPriceAssumptions, purchase_price: Decimal):
    try:
        return calculate_underwriting(replace(assumptions.underwriting, purchase_price=purchase_price))
    except ValueError as error:
        if "positive cash flow" in str(error):
            return _NoReturn()
        raise


def _meets_constraints(assumptions: MaximumPriceAssumptions, result) -> bool:
    """Return whether a probe price satisfies both constraints.

    A probe price so high that equity never receives a positive cash flow has
    no IRR; the engine reports that as an error, which the solver treats as an
    infeasible price rather than a failure of the whole search.
    """
    if isinstance(result, _NoReturn):
        return False
    # DSCR is not applicable to an all-cash acquisition. With no contractual
    # debt service, it cannot be a binding constraint on the purchase price.
    dscr_is_satisfied = result.returns.minimum_dscr is None or result.returns.minimum_dscr >= assumptions.minimum_dscr
    return result.returns.levered_irr >= assumptions.target_levered_irr and dscr_is_satisfied


class _NoReturn:
    """Marker for a probe price whose equity cash flows are never positive."""


def _binding_constraint(assumptions: MaximumPriceAssumptions, result) -> str:
    """Name the constraint that stops the price from rising further."""
    irr_headroom = result.returns.levered_irr - assumptions.target_levered_irr
    if result.returns.minimum_dscr is None:
        return "target_levered_irr"
    dscr_headroom = result.returns.minimum_dscr - assumptions.minimum_dscr
    # Compare proportional headroom so a 1bp IRR gap and a 0.001x DSCR gap are
    # judged on the same footing.
    irr_relative = irr_headroom / max(abs(assumptions.target_levered_irr), Decimal("0.0001"))
    dscr_relative = dscr_headroom / assumptions.minimum_dscr
    return "minimum_dscr" if dscr_relative < irr_relative else "target_levered_irr"
