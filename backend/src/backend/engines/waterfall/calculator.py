"""Annual preferred-return waterfall with capital calls and residual split."""

from backend.core.validation import ZERO
from backend.engines.returns import ReturnAssumptions, calculate_returns

from .models import WaterfallAssumptions, WaterfallResult, WaterfallYear


def calculate_waterfall(assumptions: WaterfallAssumptions) -> WaterfallResult:
    """Apply return of capital, accrued pref, then residual sponsor/LP split.

    Negative property cash flow is treated as an LP capital call. Preferred
    return accrues annually on beginning unreturned LP capital and carries
    forward until paid.
    """
    unreturned_capital = assumptions.initial_lp_equity
    unpaid_pref = ZERO
    lp_cash_flows = []
    years = []
    for year, property_cash_flow in enumerate(assumptions.annual_property_cash_flows, start=1):
        if property_cash_flow < ZERO:
            contribution = -property_cash_flow
            unreturned_capital += contribution
            lp_cash_flows.append(-contribution)
            years.append(WaterfallYear(year, property_cash_flow, contribution, ZERO, ZERO, ZERO, ZERO, ZERO, ZERO, unpaid_pref, unreturned_capital))
            continue
        accrued_pref = unpaid_pref + unreturned_capital * assumptions.preferred_return_rate
        remaining = property_cash_flow
        return_of_capital = min(remaining, unreturned_capital)
        remaining -= return_of_capital
        unreturned_capital -= return_of_capital
        preferred_return = min(remaining, accrued_pref)
        remaining -= preferred_return
        unpaid_pref = accrued_pref - preferred_return
        residual_to_lp = remaining * assumptions.lp_residual_share
        residual_to_sponsor = remaining * assumptions.sponsor_residual_share
        lp_distribution = return_of_capital + preferred_return + residual_to_lp
        lp_cash_flows.append(lp_distribution)
        years.append(WaterfallYear(year, property_cash_flow, ZERO, return_of_capital, preferred_return, residual_to_lp, residual_to_sponsor, lp_distribution, residual_to_sponsor, unpaid_pref, unreturned_capital))
    returns = calculate_returns(ReturnAssumptions(initial_equity=assumptions.initial_lp_equity, annual_cash_flows=tuple(lp_cash_flows)))
    total_lp_contributed = assumptions.initial_lp_equity + sum((year.lp_capital_contribution for year in years), ZERO)
    total_lp_distributed = sum((year.lp_distribution for year in years), ZERO)
    return WaterfallResult(
        years=tuple(years),
        total_lp_contributed=total_lp_contributed,
        total_lp_distributed=total_lp_distributed,
        total_sponsor_distributed=sum((year.sponsor_distribution for year in years), ZERO),
        lp_irr=returns.levered_irr,
        # Unlike a simple acquisition return, this waterfall can make
        # additional LP capital calls after closing.  The multiple must use
        # every contributed dollar, not only the initial investment.
        lp_equity_multiple=total_lp_distributed / total_lp_contributed,
    )
