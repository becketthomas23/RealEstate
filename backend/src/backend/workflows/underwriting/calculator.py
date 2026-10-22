"""Compose the independent engines into a complete underwriting run."""

from backend.core.validation import ZERO
from backend.engines.debt import DebtAssumptions, DebtYear, project_debt
from backend.engines.disposition import DispositionAssumptions, calculate_disposition
from backend.engines.operating import project_monthly_operations, project_operations, project_terminal_noi
from backend.engines.returns import ReturnAssumptions, calculate_returns
from backend.engines.risk import calculate_risk_flags

from .models import UnderwritingAssumptions, UnderwritingResult, UnleveredMetrics


def calculate_underwriting(assumptions: UnderwritingAssumptions) -> UnderwritingResult:
    """Calculate annual levered cash flow and terminal sale proceeds.

    The sale uses forward (year after hold) NOI, the standard direct-capitalization
    convention. The final annual equity cash flow includes sale proceeds.
    """
    operating_projection = project_operations(assumptions.operating)
    monthly_operating_projection = project_monthly_operations(assumptions.operating)
    debt_projection = (
        project_debt(
            DebtAssumptions(
                loan_amount=assumptions.loan_amount,
                annual_interest_rate=assumptions.annual_interest_rate,
                amortization_years=assumptions.amortization_years,
                hold_period_years=assumptions.operating.hold_period_years,
            )
        )
        if assumptions.loan_amount > ZERO
        else tuple(
            DebtYear(year, ZERO, ZERO, ZERO, ZERO, ZERO)
            for year in range(1, assumptions.operating.hold_period_years + 1)
        )
    )
    terminal_noi = project_terminal_noi(assumptions.operating)
    disposition = calculate_disposition(
        DispositionAssumptions(
            terminal_noi=terminal_noi,
            exit_cap_rate=assumptions.exit_cap_rate,
            selling_cost_rate=assumptions.selling_cost_rate,
            loan_payoff=debt_projection[-1].ending_balance,
        )
    )
    annual_operating_cash_flows = tuple(
        operating.net_operating_income - debt.debt_service
        for operating, debt in zip(operating_projection, debt_projection)
    )
    annual_cash_flows = tuple(
        cash_flow + (disposition.net_sale_proceeds_to_equity if year == assumptions.operating.hold_period_years else 0)
        for year, cash_flow in enumerate(annual_operating_cash_flows, start=1)
    )
    returns = calculate_returns(
        ReturnAssumptions(
            initial_equity=assumptions.initial_equity,
            annual_cash_flows=annual_cash_flows,
            annual_operating_cash_flows=annual_operating_cash_flows,
            annual_noi=(tuple(year.net_operating_income for year in operating_projection) if assumptions.loan_amount > ZERO else ()),
            annual_debt_service=(tuple(year.debt_service for year in debt_projection) if assumptions.loan_amount > ZERO else ()),
        )
    )
    year_one_noi = operating_projection[0].net_operating_income
    going_in_cap_rate = year_one_noi / assumptions.purchase_price
    maximum_rent_growth = max(
        assumptions.operating.rent_growth_rate_for_year(year)
        for year in range(1, assumptions.operating.hold_period_years + 2)
    )
    risk_flags = calculate_risk_flags(
        minimum_dscr=returns.minimum_dscr,
        loan_to_value=assumptions.loan_to_value,
        maximum_rent_growth=maximum_rent_growth,
        exit_cap_rate=assumptions.exit_cap_rate,
        going_in_cap_rate=going_in_cap_rate,
        annual_cash_flows=annual_cash_flows,
    )
    unlevered = _unlevered_metrics(assumptions, operating_projection, disposition)
    return UnderwritingResult(
        operating_projection=operating_projection,
        monthly_operating_projection=monthly_operating_projection,
        debt_projection=debt_projection,
        terminal_noi=terminal_noi,
        going_in_cap_rate=going_in_cap_rate,
        debt_yield=year_one_noi / assumptions.loan_amount if assumptions.loan_amount > ZERO else None,
        disposition=disposition,
        annual_operating_cash_flows=annual_operating_cash_flows,
        annual_cash_flows=annual_cash_flows,
        returns=returns,
        risk_flags=risk_flags,
        purchase_price=assumptions.purchase_price,
        loan_amount=assumptions.loan_amount,
        closing_costs=assumptions.closing_costs,
        initial_equity=assumptions.initial_equity,
        unlevered=unlevered,
        levered_profit=returns.total_equity_distributed - returns.total_equity_contributed,
        annual_debt_yield=(
            tuple(year.net_operating_income / assumptions.loan_amount for year in operating_projection)
            if assumptions.loan_amount > ZERO
            else None
        ),
    )


def _unlevered_metrics(assumptions: UnderwritingAssumptions, operating_projection, disposition) -> UnleveredMetrics:
    """Return property-level returns: NOI each year plus net sale proceeds before debt."""
    total_cost = assumptions.purchase_price + assumptions.closing_costs
    hold = assumptions.operating.hold_period_years
    cash_flows = tuple(
        year.net_operating_income + (disposition.net_sale_proceeds_before_debt if year.year == hold else ZERO)
        for year in operating_projection
    )
    distributed = sum((flow for flow in cash_flows if flow > ZERO), ZERO)
    contributed = total_cost + sum((-flow for flow in cash_flows if flow < ZERO), ZERO)
    try:
        irr = calculate_returns(ReturnAssumptions(initial_equity=total_cost, annual_cash_flows=cash_flows)).levered_irr
    except ValueError:
        irr = None
    return UnleveredMetrics(
        annual_cash_flows=cash_flows,
        irr=irr,
        multiple=distributed / contributed,
        total_cost=total_cost,
        profit=distributed - contributed,
    )
