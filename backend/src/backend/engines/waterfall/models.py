"""Contracts for the first configurable equity-waterfall structure."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import ONE, ZERO, require_non_negative, require_rate


@dataclass(frozen=True, slots=True)
class WaterfallAssumptions:
    """Single-LP preferred-return waterfall inputs.

    ``pay_preferred_return_before_capital`` selects the tier order. The
    default pays the accrued preferred return before returning capital, the
    most common structure in simple LP/sponsor agreements. Setting it to
    ``False`` returns capital first, which lowers the base that the preferred
    return accrues on and therefore favours the sponsor.
    """

    initial_lp_equity: Decimal
    annual_property_cash_flows: tuple[Decimal, ...]
    preferred_return_rate: Decimal
    sponsor_residual_share: Decimal
    pay_preferred_return_before_capital: bool = True

    def __post_init__(self) -> None:
        require_non_negative("initial_lp_equity", self.initial_lp_equity)
        if self.initial_lp_equity == ZERO:
            raise ValueError("initial_lp_equity must be greater than zero")
        if not self.annual_property_cash_flows:
            raise ValueError("annual_property_cash_flows must contain at least one year")
        require_rate("preferred_return_rate", self.preferred_return_rate)
        if not ZERO <= self.sponsor_residual_share <= ONE:
            raise ValueError("sponsor_residual_share must be between 0 and 1")

    @property
    def lp_residual_share(self) -> Decimal:
        return ONE - self.sponsor_residual_share


@dataclass(frozen=True, slots=True)
class WaterfallYear:
    year: int
    property_cash_flow: Decimal
    lp_capital_contribution: Decimal
    accrued_preferred_return: Decimal
    return_of_capital_to_lp: Decimal
    preferred_return_to_lp: Decimal
    residual_to_lp: Decimal
    residual_to_sponsor: Decimal
    lp_distribution: Decimal
    sponsor_distribution: Decimal
    unpaid_preferred_return: Decimal
    unreturned_lp_capital: Decimal


@dataclass(frozen=True, slots=True)
class WaterfallResult:
    years: tuple[WaterfallYear, ...]
    total_lp_contributed: Decimal
    total_lp_distributed: Decimal
    total_sponsor_distributed: Decimal
    lp_irr: Decimal
    lp_equity_multiple: Decimal
    pay_preferred_return_before_capital: bool
