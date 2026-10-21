from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import ONE, ZERO, require_non_negative, require_rate


@dataclass(frozen=True, slots=True)
class ConstructionLoanAssumptions:
    monthly_project_costs: tuple[Decimal, ...]
    loan_to_cost: Decimal
    annual_interest_rate: Decimal
    origination_fee_rate: Decimal = ZERO

    def __post_init__(self) -> None:
        if not self.monthly_project_costs:
            raise ValueError("monthly_project_costs must contain at least one month")
        for cost in self.monthly_project_costs:
            require_non_negative("monthly_project_costs", cost)
        if not ZERO < self.loan_to_cost <= ONE:
            raise ValueError("loan_to_cost must be greater than 0 and no more than 1")
        require_rate("annual_interest_rate", self.annual_interest_rate)
        require_rate("origination_fee_rate", self.origination_fee_rate)


@dataclass(frozen=True, slots=True)
class ConstructionMonth:
    month: int
    project_cost: Decimal
    loan_draw: Decimal
    equity_contribution: Decimal
    beginning_loan_balance: Decimal
    capitalized_interest: Decimal
    ending_loan_balance: Decimal


@dataclass(frozen=True, slots=True)
class ConstructionLoanResult:
    months: tuple[ConstructionMonth, ...]
    total_project_cost: Decimal
    total_equity_contribution: Decimal
    origination_fee: Decimal
    total_capitalized_interest: Decimal
    ending_loan_balance: Decimal
