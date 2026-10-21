"""Input and output contracts for the returns engine."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import ZERO, require_positive


@dataclass(frozen=True, slots=True)
class ReturnAssumptions:
    initial_equity: Decimal
    annual_cash_flows: tuple[Decimal, ...]
    annual_noi: tuple[Decimal, ...] = ()
    annual_debt_service: tuple[Decimal, ...] = ()
    # Recurring cash flow excludes a terminal sale.  It is optional so the
    # generic return engine remains useful for capital structures that do not
    # distinguish operating cash flow from other distributions.  It stays
    # after the original optional arguments to preserve positional callers.
    annual_operating_cash_flows: tuple[Decimal, ...] = ()

    def __post_init__(self) -> None:
        require_positive("initial_equity", self.initial_equity)
        if not self.annual_cash_flows:
            raise ValueError("annual_cash_flows must contain at least one year")
        if self.annual_operating_cash_flows and len(self.annual_operating_cash_flows) != len(self.annual_cash_flows):
            raise ValueError("annual_operating_cash_flows must have the same length as annual_cash_flows")
        if bool(self.annual_noi) != bool(self.annual_debt_service) or len(self.annual_noi) != len(self.annual_debt_service):
            raise ValueError("annual_noi and annual_debt_service must both be omitted or have matching lengths")
        if any(value <= ZERO for value in self.annual_debt_service):
            raise ValueError("annual_debt_service values must be greater than zero")


@dataclass(frozen=True, slots=True)
class ReturnMetrics:
    levered_irr: Decimal
    equity_multiple: Decimal
    total_equity_contributed: Decimal
    total_equity_distributed: Decimal
    cash_on_cash_by_year: tuple[Decimal, ...]
    dscr_by_year: tuple[Decimal, ...]
    minimum_dscr: Decimal | None
