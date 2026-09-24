"""Annual stabilized-property operating pro-forma calculations."""

from backend.core.validation import ONE

from .models import OperatingAssumptions, OperatingYear


def project_operations(assumptions: OperatingAssumptions) -> tuple[OperatingYear, ...]:
    """Return an immutable annual operating projection."""
    years: list[OperatingYear] = []
    for year in range(1, assumptions.hold_period_years + 1):
        income = assumptions.current_potential_gross_income * (ONE + assumptions.rent_growth_rate) ** year
        expenses = assumptions.current_operating_expenses * (ONE + assumptions.expense_growth_rate) ** year
        vacancy_loss = income * assumptions.vacancy_rate
        effective_income = income - vacancy_loss
        years.append(OperatingYear(year, income, vacancy_loss, effective_income, expenses, effective_income - expenses))
    return tuple(years)
