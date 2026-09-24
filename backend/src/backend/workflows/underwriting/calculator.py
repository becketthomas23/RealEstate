"""Compose the independent engines into a complete underwriting run."""

from backend.core.validation import ONE
from backend.engines.debt import DebtAssumptions, project_debt
from backend.engines.disposition import DispositionAssumptions, calculate_disposition
from backend.engines.operating import project_operations
from backend.engines.returns import ReturnAssumptions, calculate_returns

from .models import UnderwritingAssumptions, UnderwritingResult


def calculate_underwriting(assumptions: UnderwritingAssumptions) -> UnderwritingResult:
    """Calculate annual levered cash flow and terminal sale proceeds.

    The sale uses forward (year after hold) NOI, the standard direct-capitalization
    convention. The final annual equity cash flow includes sale proceeds.
    """
    operating_projection = project_operations(assumptions.operating)
    debt_projection = project_debt(
        DebtAssumptions(
            loan_amount=assumptions.loan_amount,
            annual_interest_rate=assumptions.annual_interest_rate,
            amortization_years=assumptions.amortization_years,
            hold_period_years=assumptions.operating.hold_period_years,
        )
    )
    terminal_noi = _terminal_noi(assumptions)
    disposition = calculate_disposition(
        DispositionAssumptions(
            terminal_noi=terminal_noi,
            exit_cap_rate=assumptions.exit_cap_rate,
            selling_cost_rate=assumptions.selling_cost_rate,
            loan_payoff=debt_projection[-1].ending_balance,
        )
    )
    annual_cash_flows = tuple(
        operating.net_operating_income - debt.debt_service + (disposition.net_sale_proceeds_to_equity if operating.year == assumptions.operating.hold_period_years else 0)
        for operating, debt in zip(operating_projection, debt_projection)
    )
    returns = calculate_returns(
        ReturnAssumptions(
            initial_equity=assumptions.initial_equity,
            annual_cash_flows=annual_cash_flows,
            annual_noi=tuple(year.net_operating_income for year in operating_projection),
            annual_debt_service=tuple(year.debt_service for year in debt_projection),
        )
    )
    return UnderwritingResult(operating_projection, debt_projection, terminal_noi, disposition, annual_cash_flows, returns)


def _terminal_noi(assumptions: UnderwritingAssumptions):
    """Project next year's NOI for use in the sale calculation."""
    operating = assumptions.operating
    exponent = operating.hold_period_years + 1
    income = operating.current_potential_gross_income * (ONE + operating.rent_growth_rate) ** exponent
    expenses = operating.current_operating_expenses * (ONE + operating.expense_growth_rate) ** exponent
    return income * (ONE - operating.vacancy_rate) - expenses
