"""Annual stabilized-property operating pro-forma calculations."""

from backend.core.validation import ONE, ZERO

from .models import OperatingAssumptions, OperatingMonth, OperatingYear


def project_operations(assumptions: OperatingAssumptions) -> tuple[OperatingYear, ...]:
    """Return an immutable annual operating projection for the hold period."""
    return tuple(project_operating_year(assumptions, year) for year in range(1, assumptions.hold_period_years + 1))


def project_operating_year(assumptions: OperatingAssumptions, year: int) -> OperatingYear:
    """Project any single year, including the forward year used for a sale.

    Income compounds through the per-year rent-growth schedule; expenses grow
    at the single expense-growth rate for the same number of growth periods.
    """
    income = assumptions.current_potential_gross_income
    for growth_year in range(1, year + 1):
        income *= ONE + assumptions.rent_growth_rate_for_year(growth_year)
    expenses = assumptions.current_operating_expenses * (ONE + assumptions.expense_growth_rate) ** assumptions.growth_periods_through(year)
    vacancy_loss = income * assumptions.vacancy_rate
    effective_income = income - vacancy_loss
    return OperatingYear(year, income, vacancy_loss, effective_income, expenses, effective_income - expenses)


def project_terminal_noi(assumptions: OperatingAssumptions):
    """Return the forward NOI for the year after the hold, used to size the sale."""
    return project_operating_year(assumptions, assumptions.hold_period_years + 1).net_operating_income


def project_monthly_operations(assumptions: OperatingAssumptions) -> tuple[OperatingMonth, ...]:
    """Return a monthly projection that reconciles exactly to annual results."""
    months: list[OperatingMonth] = []
    for annual in project_operations(assumptions):
        income = _monthly_amounts(annual.potential_gross_income)
        vacancy = _monthly_amounts(annual.vacancy_loss)
        effective_income = _monthly_amounts(annual.effective_gross_income)
        expenses = _monthly_amounts(annual.operating_expenses)
        net_operating_income = _monthly_amounts(annual.net_operating_income)
        for month_in_year in range(1, 13):
            index = month_in_year - 1
            months.append(
                OperatingMonth(
                    month=(annual.year - 1) * 12 + month_in_year,
                    year=annual.year,
                    month_in_year=month_in_year,
                    potential_gross_income=income[index],
                    vacancy_loss=vacancy[index],
                    effective_gross_income=effective_income[index],
                    operating_expenses=expenses[index],
                    # Allocate NOI independently so the monthly cash-flow line
                    # reconciles exactly to the audited annual NOI despite
                    # finite Decimal precision in one-twelfth allocations.
                    net_operating_income=net_operating_income[index],
                )
            )
    return tuple(months)


def _monthly_amounts(annual_amount):
    """Allocate an annual Decimal across twelve periods without reconciliation drift."""
    regular_amount = annual_amount / 12
    first_eleven = (regular_amount,) * 11
    # Use the same accumulation order consumers use when rolling up the months.
    # Decimal arithmetic has finite precision, so multiplication would not always
    # leave a residual that exactly offsets repeated addition.
    return first_eleven + (annual_amount - sum(first_eleven, ZERO),)
