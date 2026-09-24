"""Property-sale-proceeds calculations."""

from .models import DispositionAssumptions, DispositionResult


def calculate_disposition(assumptions: DispositionAssumptions) -> DispositionResult:
    gross_sale_price = assumptions.terminal_noi / assumptions.exit_cap_rate
    selling_costs = gross_sale_price * assumptions.selling_cost_rate
    before_debt = gross_sale_price - selling_costs
    return DispositionResult(gross_sale_price, selling_costs, before_debt, assumptions.loan_payoff, before_debt - assumptions.loan_payoff)
