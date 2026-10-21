"""Contracts for an integrated construction, refinance, and hold-period model."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import ONE, ZERO, require_rate
from backend.engines.construction import ConstructionLoanAssumptions, ConstructionLoanResult
from backend.engines.debt import DebtYear
from backend.engines.disposition import DispositionResult
from backend.engines.operating import OperatingAssumptions, OperatingYear
from backend.engines.returns import ReturnMetrics


@dataclass(frozen=True, slots=True)
class DevelopmentAssumptions:
    """Inputs for a construction-funded project refinanced into permanent debt.

    Construction takes place before the first stabilized operating year. The
    model therefore reports construction equity at time zero, a refinance at
    the start of the stabilized hold, and then annual operating cash flows.
    """

    construction: ConstructionLoanAssumptions
    operating: OperatingAssumptions
    stabilization_cap_rate: Decimal
    permanent_loan_to_value: Decimal
    permanent_interest_rate: Decimal
    permanent_amortization_years: int
    exit_cap_rate: Decimal
    selling_cost_rate: Decimal
    refinance_cost_rate: Decimal = ZERO

    def __post_init__(self) -> None:
        if not ZERO < self.stabilization_cap_rate < ONE:
            raise ValueError("stabilization_cap_rate must be between 0 and 1")
        if not ZERO < self.permanent_loan_to_value < ONE:
            raise ValueError("permanent_loan_to_value must be between 0 and 1")
        require_rate("permanent_interest_rate", self.permanent_interest_rate)
        if self.permanent_amortization_years < self.operating.hold_period_years:
            raise ValueError("permanent_amortization_years must be at least the hold period")
        if not ZERO < self.exit_cap_rate < ONE:
            raise ValueError("exit_cap_rate must be between 0 and 1")
        require_rate("selling_cost_rate", self.selling_cost_rate)
        require_rate("refinance_cost_rate", self.refinance_cost_rate)


@dataclass(frozen=True, slots=True)
class RefinanceResult:
    stabilized_value: Decimal
    permanent_loan_amount: Decimal
    refinance_costs: Decimal
    construction_loan_payoff: Decimal
    net_refinance_proceeds: Decimal
    additional_equity_required: Decimal


@dataclass(frozen=True, slots=True)
class DevelopmentResult:
    construction: ConstructionLoanResult
    operating_projection: tuple[OperatingYear, ...]
    permanent_debt_projection: tuple[DebtYear, ...]
    terminal_noi: Decimal
    disposition: DispositionResult
    refinance: RefinanceResult
    initial_equity_required: Decimal
    annual_cash_flows: tuple[Decimal, ...]
    returns: ReturnMetrics
