"""Contracts for a complete stabilized-property underwriting run."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import ONE, ZERO, require_positive, require_rate
from backend.engines.debt import DebtYear
from backend.engines.disposition import DispositionResult
from backend.engines.operating import OperatingAssumptions, OperatingMonth, OperatingYear
from backend.engines.returns import ReturnMetrics
from backend.engines.risk import RiskFlag


@dataclass(frozen=True, slots=True)
class UnderwritingAssumptions:
    """All deal assumptions needed to produce levered annual cash flows."""

    purchase_price: Decimal
    closing_cost_rate: Decimal
    loan_to_value: Decimal
    annual_interest_rate: Decimal
    amortization_years: int
    exit_cap_rate: Decimal
    selling_cost_rate: Decimal
    operating: OperatingAssumptions

    def __post_init__(self) -> None:
        require_positive("purchase_price", self.purchase_price)
        require_rate("closing_cost_rate", self.closing_cost_rate)
        if not ZERO <= self.loan_to_value < ONE:
            raise ValueError("loan_to_value must be between 0 (inclusive) and 1")
        require_rate("annual_interest_rate", self.annual_interest_rate)
        if self.amortization_years < self.operating.hold_period_years:
            raise ValueError("amortization_years must be at least the hold period")
        if not ZERO < self.exit_cap_rate < ONE:
            raise ValueError("exit_cap_rate must be between 0 and 1")
        require_rate("selling_cost_rate", self.selling_cost_rate)

    @property
    def loan_amount(self) -> Decimal:
        return self.purchase_price * self.loan_to_value

    @property
    def closing_costs(self) -> Decimal:
        return self.purchase_price * self.closing_cost_rate

    @property
    def initial_equity(self) -> Decimal:
        """Equity funds the price plus closing costs; closing costs are not financed."""
        return self.purchase_price + self.closing_costs - self.loan_amount


@dataclass(frozen=True, slots=True)
class UnleveredMetrics:
    """Property-level returns before financing, on total cost (price plus closing costs)."""

    annual_cash_flows: tuple[Decimal, ...]
    irr: Decimal | None
    multiple: Decimal
    total_cost: Decimal
    profit: Decimal


@dataclass(frozen=True, slots=True)
class UnderwritingResult:
    operating_projection: tuple[OperatingYear, ...]
    monthly_operating_projection: tuple[OperatingMonth, ...]
    debt_projection: tuple[DebtYear, ...]
    terminal_noi: Decimal
    # Year 1 NOI divided by purchase price. With the default Year 1 convention
    # this equals the current (in-place) NOI yield.
    going_in_cap_rate: Decimal
    debt_yield: Decimal | None
    disposition: DispositionResult
    annual_operating_cash_flows: tuple[Decimal, ...]
    annual_cash_flows: tuple[Decimal, ...]
    returns: ReturnMetrics
    risk_flags: tuple[RiskFlag, ...]
    purchase_price: Decimal
    loan_amount: Decimal
    closing_costs: Decimal
    initial_equity: Decimal
    unlevered: UnleveredMetrics
    # Levered profit: every distribution less every contribution.
    levered_profit: Decimal
    # Annual debt yield on the original loan amount (None for all-cash).
    annual_debt_yield: tuple[Decimal, ...] | None
