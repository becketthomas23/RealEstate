"""Levered-return and debt-coverage calculations."""

from decimal import Decimal

from backend.core.validation import ONE, ZERO

from .models import ReturnAssumptions, ReturnMetrics


LOWER_IRR_BOUND = Decimal("-0.9999")


def calculate_returns(assumptions: ReturnAssumptions) -> ReturnMetrics:
    cash_flows = (-assumptions.initial_equity, *assumptions.annual_cash_flows)
    dscr = tuple(noi / debt_service for noi, debt_service in zip(assumptions.annual_noi, assumptions.annual_debt_service))
    total_contributed = assumptions.initial_equity + sum((-flow for flow in assumptions.annual_cash_flows if flow < ZERO), ZERO)
    total_distributed = sum((flow for flow in assumptions.annual_cash_flows if flow > ZERO), ZERO)
    multiple = total_distributed / total_contributed
    # Cash-on-cash is a recurring operating-return metric.  A sale proceeds
    # distribution belongs in IRR and equity multiple, but including it here
    # would make the final year's cash-on-cash look like an operating yield.
    operating_cash_flows = assumptions.annual_operating_cash_flows or assumptions.annual_cash_flows
    cash_on_cash = tuple(flow / assumptions.initial_equity for flow in operating_cash_flows)
    return ReturnMetrics(
        _irr(cash_flows),
        multiple,
        total_contributed,
        total_distributed,
        cash_on_cash,
        dscr,
        min(dscr) if dscr else None,
    )


def _irr(cash_flows: tuple[Decimal, ...]) -> Decimal:
    if not any(value > ZERO for value in cash_flows[1:]):
        raise ValueError("annual_cash_flows must include a positive cash flow to calculate IRR")
    if _has_multiple_irr_roots(cash_flows):
        raise ValueError(
            "annual_cash_flows have multiple valid IRRs, so IRR is ambiguous; "
            "model interim funding or use a return metric with explicit reinvestment assumptions"
        )
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


def _has_multiple_irr_roots(cash_flows: tuple[Decimal, ...]) -> bool:
    """Detect distinct, positive-discount-factor IRR roots before solving.

    Several cash-flow sign changes merely *permit* multiple IRRs; they do not
    prove one exists.  A coarse-to-wide rate grid catches separate NPV
    crossings (including common development and capital-call patterns) without
    rejecting a cash flow that still has a unique meaningful IRR.
    """
    rates = (
        LOWER_IRR_BOUND, Decimal("-0.99"), Decimal("-0.90"), Decimal("-0.75"),
        Decimal("-0.50"), Decimal("-0.25"), Decimal("-0.10"), Decimal("-0.01"),
        ZERO, Decimal("0.01"), Decimal("0.02"), Decimal("0.05"), Decimal("0.10"),
        Decimal("0.15"), Decimal("0.20"), Decimal("0.25"), Decimal("0.50"), ONE,
        Decimal("2"), Decimal("5"), Decimal("10"), Decimal("100"), Decimal("1000"),
        Decimal("10000"), Decimal("1000000"),
    )
    roots = 0
    prior_value = _npv(cash_flows, rates[0])
    for rate in rates[1:]:
        value = _npv(cash_flows, rate)
        if value == ZERO:
            roots += 1
        elif prior_value != ZERO and (prior_value > ZERO) != (value > ZERO):
            roots += 1
        if roots > 1:
            return True
        prior_value = value
    return False
