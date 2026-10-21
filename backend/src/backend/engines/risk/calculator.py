"""Small, inspectable rules for material underwriting risks."""

from decimal import Decimal

from backend.core.validation import ZERO

from .models import RiskFlag


DSCR_CRITICAL = Decimal("1.00")
DSCR_WARNING = Decimal("1.20")
LTV_WARNING = Decimal("0.80")
RENT_GROWTH_WARNING = Decimal("0.05")


def calculate_risk_flags(
    *,
    minimum_dscr: Decimal | None,
    loan_to_value: Decimal,
    maximum_rent_growth: Decimal,
    exit_cap_rate: Decimal,
    going_in_cap_rate: Decimal,
    annual_cash_flows: tuple[Decimal, ...],
) -> tuple[RiskFlag, ...]:
    """Return deterministic flags with each threshold visible to the analyst."""
    flags: list[RiskFlag] = []
    if minimum_dscr is not None:
        if minimum_dscr < DSCR_CRITICAL:
            flags.append(RiskFlag("dscr_below_one", "critical", "Minimum DSCR is below 1.00x; operations do not cover debt service.", minimum_dscr, DSCR_CRITICAL))
        elif minimum_dscr < DSCR_WARNING:
            flags.append(RiskFlag("thin_dscr", "warning", "Minimum DSCR is below the 1.20x cushion.", minimum_dscr, DSCR_WARNING))
    if loan_to_value >= LTV_WARNING:
        flags.append(RiskFlag("high_leverage", "warning", "Loan-to-value is at or above 80%.", loan_to_value, LTV_WARNING))
    if maximum_rent_growth > RENT_GROWTH_WARNING:
        flags.append(RiskFlag("aggressive_rent_growth", "warning", "The rent-growth forecast exceeds 5.0% in at least one year.", maximum_rent_growth, RENT_GROWTH_WARNING))
    if exit_cap_rate < going_in_cap_rate:
        flags.append(RiskFlag("exit_cap_compression", "warning", "The exit cap rate is below the going-in cap rate, implying cap-rate compression.", exit_cap_rate, going_in_cap_rate))
    if any(cash_flow < ZERO for cash_flow in annual_cash_flows):
        flags.append(RiskFlag("negative_equity_cash_flow", "warning", "At least one projected annual equity cash flow is negative.", min(annual_cash_flows), ZERO))
    return tuple(flags)
