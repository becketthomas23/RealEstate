"""Monthly debt amortization with annual reporting aggregation."""

from decimal import Decimal

from backend.core.validation import ONE, ZERO

from .models import DebtAssumptions, DebtMonth, DebtYear


MONTHS_PER_YEAR = Decimal("12")


def project_debt(assumptions: DebtAssumptions) -> tuple[DebtYear, ...]:
    """Aggregate a monthly fixed-rate schedule into annual cash-flow reporting.

    The model reports annual cash flows, while payment, interest, principal, and
    sale-date payoff are calculated from a monthly amortization schedule.
    Decimal precision is retained until the presentation layer rounds it.
    """
    monthly_schedule = project_monthly_debt(assumptions)
    years: list[DebtYear] = []
    for year in range(1, assumptions.hold_period_years + 1):
        months = monthly_schedule[(year - 1) * 12 : year * 12]
        years.append(
            DebtYear(
                year=year,
                beginning_balance=months[0].beginning_balance,
                debt_service=sum((month.debt_service for month in months), ZERO),
                interest=sum((month.interest for month in months), ZERO),
                principal=sum((month.principal for month in months), ZERO),
                ending_balance=months[-1].ending_balance,
            )
        )
    return tuple(years)


def project_monthly_debt(assumptions: DebtAssumptions) -> tuple[DebtMonth, ...]:
    """Project monthly principal-and-interest installments through the hold."""
    total_months = assumptions.amortization_years * 12
    hold_months = assumptions.hold_period_years * 12
    monthly_rate = assumptions.annual_interest_rate / MONTHS_PER_YEAR
    payment = _monthly_payment(assumptions.loan_amount, monthly_rate, total_months)
    balance = assumptions.loan_amount
    schedule: list[DebtMonth] = []
    for month in range(1, hold_months + 1):
        interest = balance * monthly_rate
        principal = balance if month == total_months else min(payment - interest, balance)
        debt_service = interest + principal
        ending_balance = balance - principal
        schedule.append(
            DebtMonth(month, (month - 1) // 12 + 1, balance, debt_service, interest, principal, ending_balance)
        )
        balance = ending_balance
    return tuple(schedule)


def _monthly_payment(loan_amount: Decimal, monthly_rate: Decimal, total_months: int) -> Decimal:
    if monthly_rate == ZERO:
        return loan_amount / Decimal(total_months)
    return loan_amount * monthly_rate / (ONE - (ONE + monthly_rate) ** -total_months)
