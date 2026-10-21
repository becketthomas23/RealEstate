from backend.core.validation import ZERO

from .models import ConstructionLoanAssumptions, ConstructionLoanResult, ConstructionMonth


def project_construction_loan(assumptions: ConstructionLoanAssumptions) -> ConstructionLoanResult:
    """Fund monthly cost draws and capitalize interest on beginning balances.

    Interest begins in the month after a draw, reflecting an end-of-month draw
    convention. Origination fees are cash equity costs and are not financed.
    """
    balance = ZERO
    months = []
    monthly_rate = assumptions.annual_interest_rate / 12
    for month, project_cost in enumerate(assumptions.monthly_project_costs, start=1):
        loan_draw = project_cost * assumptions.loan_to_cost
        equity = project_cost - loan_draw
        interest = balance * monthly_rate
        ending_balance = balance + interest + loan_draw
        months.append(ConstructionMonth(month, project_cost, loan_draw, equity, balance, interest, ending_balance))
        balance = ending_balance
    total_draws = sum((month.loan_draw for month in months), ZERO)
    fee = total_draws * assumptions.origination_fee_rate
    return ConstructionLoanResult(
        months=tuple(months),
        total_project_cost=sum(assumptions.monthly_project_costs, ZERO),
        total_equity_contribution=sum((month.equity_contribution for month in months), ZERO) + fee,
        origination_fee=fee,
        total_capitalized_interest=sum((month.capitalized_interest for month in months), ZERO),
        ending_loan_balance=balance,
    )
