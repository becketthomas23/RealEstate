"""Input and output contracts for the operating pro-forma engine."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import ONE, require_non_negative, require_positive, require_rate


@dataclass(frozen=True, slots=True)
class OperatingAssumptions:
    current_potential_gross_income: Decimal
    current_operating_expenses: Decimal
    vacancy_rate: Decimal
    rent_growth_rate: Decimal
    expense_growth_rate: Decimal
    hold_period_years: int

    def __post_init__(self) -> None:
        require_positive("current_potential_gross_income", self.current_potential_gross_income)
        require_non_negative("current_operating_expenses", self.current_operating_expenses)
        require_rate("vacancy_rate", self.vacancy_rate)
        require_rate("rent_growth_rate", self.rent_growth_rate, allow_negative=True)
        require_rate("expense_growth_rate", self.expense_growth_rate, allow_negative=True)
        if not 5 <= self.hold_period_years <= 10:
            raise ValueError("hold_period_years must be between 5 and 10")

    @property
    def current_noi(self) -> Decimal:
        return self.current_potential_gross_income * (ONE - self.vacancy_rate) - self.current_operating_expenses


@dataclass(frozen=True, slots=True)
class OperatingYear:
    year: int
    potential_gross_income: Decimal
    vacancy_loss: Decimal
    effective_gross_income: Decimal
    operating_expenses: Decimal
    net_operating_income: Decimal
