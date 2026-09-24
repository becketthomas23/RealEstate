"""Levered-return and debt-coverage calculations."""

from decimal import Decimal

from backend.core.validation import ONE, ZERO

from .models import ReturnAssumptions, ReturnMetrics


LOWER_IRR_BOUND = Decimal("-0.9999")


def calculate_returns(assumptions: ReturnAssumptions) -> ReturnMetrics:
    cash_flows = (-assumptions.initial_equity, *assumptions.annual_cash_flows)
    dscr = tuple(noi / debt_service for noi, debt_service in zip(assumptions.annual_noi, assumptions.annual_debt_service))
    multiple = sum((flow for flow in assumptions.annual_cash_flows if flow > ZERO), ZERO) / assumptions.initial_equity
    return ReturnMetrics(_irr(cash_flows), multiple, dscr, min(dscr) if dscr else None)


def _irr(cash_flows: tuple[Decimal, ...]) -> Decimal:
    if not any(value > ZERO for value in cash_flows[1:]):
        raise ValueError("annual_cash_flows must include a positive cash flow to calculate IRR")
    low, high = LOWER_IRR_BOUND, ONE
    while _npv(cash_flows, high) > ZERO and high < Decimal("1000000"):
        high *= Decimal("2")
    if _npv(cash_flows, low) * _npv(cash_flows, high) > ZERO:
        raise ValueError("could not bracket an IRR for these cash flows")
    for _ in range(100):
        midpoint = (low + high) / Decimal("2")
        if _npv(cash_flows, midpoint) > ZERO:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / Decimal("2")


def _npv(cash_flows: tuple[Decimal, ...], rate: Decimal) -> Decimal:
    return sum((flow / (ONE + rate) ** period for period, flow in enumerate(cash_flows)), ZERO)
