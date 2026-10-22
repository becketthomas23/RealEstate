"""Compose construction financing, stabilization, permanent debt, and exit."""

from backend.core.validation import ZERO
from backend.engines.construction import project_construction_loan
from backend.engines.debt import DebtAssumptions, project_debt
from backend.engines.disposition import DispositionAssumptions, calculate_disposition
from backend.engines.operating import project_operations, project_terminal_noi
from backend.engines.returns import ReturnAssumptions, calculate_returns

from .models import DevelopmentAssumptions, DevelopmentResult, RefinanceResult


def calculate_development(assumptions: DevelopmentAssumptions) -> DevelopmentResult:
    """Underwrite a build, permanent-loan refinance, stabilized hold, and sale.

    Capitalized construction interest remains in the construction balance. At
    stabilization, permanent-loan proceeds first pay that balance and all
    refinance costs. A shortfall is an additional initial equity contribution;
    positive proceeds are included in the first stabilized-year cash flow.
    """
    construction = project_construction_loan(assumptions.construction)
    operating_projection = project_operations(assumptions.operating)
    stabilized_value = operating_projection[0].net_operating_income / assumptions.stabilization_cap_rate
    permanent_loan_amount = stabilized_value * assumptions.permanent_loan_to_value
    permanent_debt_projection = project_debt(
        DebtAssumptions(
            loan_amount=permanent_loan_amount,
            annual_interest_rate=assumptions.permanent_interest_rate,
            amortization_years=assumptions.permanent_amortization_years,
            hold_period_years=assumptions.operating.hold_period_years,
        )
    )
    refinance_costs = permanent_loan_amount * assumptions.refinance_cost_rate
    net_refinance_proceeds = permanent_loan_amount - construction.ending_loan_balance - refinance_costs
    additional_equity_required = max(-net_refinance_proceeds, ZERO)
    refinance = RefinanceResult(
        stabilized_value=stabilized_value,
        permanent_loan_amount=permanent_loan_amount,
        refinance_costs=refinance_costs,
        construction_loan_payoff=construction.ending_loan_balance,
        net_refinance_proceeds=net_refinance_proceeds,
        additional_equity_required=additional_equity_required,
    )
    terminal_noi = project_terminal_noi(assumptions.operating)
    disposition = calculate_disposition(
        DispositionAssumptions(
            terminal_noi=terminal_noi,
            exit_cap_rate=assumptions.exit_cap_rate,
            selling_cost_rate=assumptions.selling_cost_rate,
            loan_payoff=permanent_debt_projection[-1].ending_balance,
        )
    )
    initial_equity_required = construction.total_equity_contribution + additional_equity_required
    annual_cash_flows = tuple(
        operating.net_operating_income
        - debt.debt_service
        + (max(net_refinance_proceeds, ZERO) if operating.year == 1 else ZERO)
        + (disposition.net_sale_proceeds_to_equity if operating.year == assumptions.operating.hold_period_years else ZERO)
        for operating, debt in zip(operating_projection, permanent_debt_projection, strict=True)
    )
    returns = calculate_returns(
        ReturnAssumptions(
            initial_equity=initial_equity_required,
            annual_cash_flows=annual_cash_flows,
            annual_noi=tuple(year.net_operating_income for year in operating_projection),
            annual_debt_service=tuple(year.debt_service for year in permanent_debt_projection),
        )
    )
    return DevelopmentResult(
        construction=construction,
        operating_projection=operating_projection,
        permanent_debt_projection=permanent_debt_projection,
        terminal_noi=terminal_noi,
        disposition=disposition,
        refinance=refinance,
        initial_equity_required=initial_equity_required,
        annual_cash_flows=annual_cash_flows,
        returns=returns,
    )

