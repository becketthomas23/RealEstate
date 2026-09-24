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

    def __post_init__(self) -> None:
        require_positive("initial_equity", self.initial_equity)
        if not self.annual_cash_flows:
            raise ValueError("annual_cash_flows must contain at least one year")
        if bool(self.annual_noi) != bool(self.annual_debt_service) or len(self.annual_noi) != len(self.annual_debt_service):
            raise ValueError("annual_noi and annual_debt_service must both be omitted or have matching lengths")
        if any(value <= ZERO for value in self.annual_debt_service):
            raise ValueError("annual_debt_service values must be greater than zero")


@dataclass(frozen=True, slots=True)
class ReturnMetrics:
    levered_irr: Decimal
    equity_multiple: Decimal
    dscr_by_year: tuple[Decimal, ...]
    minimum_dscr: Decimal | None
