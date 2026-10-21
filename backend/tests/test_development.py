from dataclasses import replace
from decimal import Decimal
import unittest

from backend.engines.construction import ConstructionLoanAssumptions
from backend.engines.operating import OperatingAssumptions
from backend.workflows.development import DevelopmentAssumptions, calculate_development


D = Decimal


class DevelopmentWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assumptions = DevelopmentAssumptions(
            construction=ConstructionLoanAssumptions(
                monthly_project_costs=(D("100"), D("200")),
                loan_to_cost=D("0.70"),
                annual_interest_rate=D("0.12"),
                origination_fee_rate=D("0.01"),
            ),
            operating=OperatingAssumptions(
                current_potential_gross_income=D("2000"),
                current_operating_expenses=D("500"),
                vacancy_rate=D("0.10"),
                rent_growth_rate=D("0"),
                expense_growth_rate=D("0"),
                hold_period_years=5,
            ),
            stabilization_cap_rate=D("0.10"),
            permanent_loan_to_value=D("0.60"),
            permanent_interest_rate=D("0"),
            permanent_amortization_years=30,
            exit_cap_rate=D("0.10"),
            selling_cost_rate=D("0.02"),
            refinance_cost_rate=D("0.01"),
        )

    def test_links_construction_refinance_operation_and_exit_cash_flows(self) -> None:
        result = calculate_development(self.assumptions)

        self.assertEqual(result.construction.ending_loan_balance, D("210.7000"))
        self.assertEqual(result.refinance.stabilized_value, D("13000"))
        self.assertEqual(result.refinance.permanent_loan_amount, D("7800.00"))
        self.assertEqual(result.refinance.refinance_costs, D("78.0000"))
        self.assertEqual(result.refinance.net_refinance_proceeds, D("7511.3000"))
        self.assertEqual(result.refinance.additional_equity_required, D("0"))
        self.assertEqual(result.initial_equity_required, D("92.10"))
        self.assertEqual(result.annual_cash_flows[0], D("8551.3000"))
        self.assertAlmostEqual(result.disposition.loan_payoff, D("6500"), places=18)
        self.assertGreater(result.returns.levered_irr, D("0"))

    def test_refinance_shortfall_increases_required_equity_without_negative_distribution(self) -> None:
        result = calculate_development(replace(self.assumptions, permanent_loan_to_value=D("0.01")))

        self.assertLess(result.refinance.net_refinance_proceeds, D("0"))
        self.assertEqual(result.annual_cash_flows[0], D("1295.666666666666666666666667"))
        self.assertEqual(
            result.initial_equity_required,
            result.construction.total_equity_contribution + result.refinance.additional_equity_required,
        )
