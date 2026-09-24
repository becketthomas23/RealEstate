"""Input and output contracts for the debt engine."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import ONE, ZERO, require_positive, require_rate


@dataclass(frozen=True, slots=True)
class DebtAssumptions:
    loan_amount: Decimal
    annual_interest_rate: Decimal
    amortization_years: int
    hold_period_years: int

    def __post_init__(self) -> None:
        require_positive("loan_amount", self.loan_amount)
        require_rate("annual_interest_rate", self.annual_interest_rate)
        if self.amortization_years < 1:
            raise ValueError("amortization_years must be at least 1")
        if not 5 <= self.hold_period_years <= 10:
            raise ValueError("hold_period_years must be between 5 and 10")
        if self.amortization_years < self.hold_period_years:
            raise ValueError("amortization_years must be at least the hold period")


@dataclass(frozen=True, slots=True)
class DebtMonth:
    """One monthly principal-and-interest installment."""

    month: int
    year: int
    beginning_balance: Decimal
    debt_service: Decimal
    interest: Decimal
    principal: Decimal
    ending_balance: Decimal


@dataclass(frozen=True, slots=True)
class DebtYear:
    year: int
    beginning_balance: Decimal
    debt_service: Decimal
    interest: Decimal
    principal: Decimal
    ending_balance: Decimal
