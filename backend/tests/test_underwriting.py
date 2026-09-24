"""Hand-calculated integration fixture across every calculation engine."""

from decimal import Decimal
import unittest

from backend.engines.operating import OperatingAssumptions
from backend.workflows.underwriting import UnderwritingAssumptions, calculate_underwriting


D = Decimal


class UnderwritingWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        # Flat NOI and zero interest make this five-year example hand-checkable.
        self.assumptions = UnderwritingAssumptions(
            purchase_price=D("1000000"),
            closing_cost_rate=D("0.02"),
            loan_to_value=D("0.60"),
            annual_interest_rate=D("0"),
            amortization_years=5,
            exit_cap_rate=D("0.10"),
            selling_cost_rate=D("0.02"),
            operating=OperatingAssumptions(
                current_potential_gross_income=D("200000"),
                current_operating_expenses=D("50000"),
                vacancy_rate=D("0.10"),
                rent_growth_rate=D("0"),
                expense_growth_rate=D("0"),
                hold_period_years=5,
            ),
        )

    def test_links_operations_debt_disposition_and_returns(self) -> None:
        result = calculate_underwriting(self.assumptions)

        self.assertEqual(self.assumptions.initial_equity, D("420000.00"))
        self.assertEqual(result.operating_projection[0].net_operating_income, D("130000.00"))
        self.assertEqual(result.debt_projection[0].debt_service, D("120000"))
        self.assertEqual(result.terminal_noi, D("130000.00"))
        self.assertEqual(result.disposition.gross_sale_price, D("1300000.0"))
        self.assertEqual(result.disposition.net_sale_proceeds_to_equity, D("1274000.000"))
        self.assertEqual(result.annual_cash_flows, (D("10000.00"),) * 4 + (D("1284000.000"),))
        self.assertEqual(result.returns.dscr_by_year, (D("1.083333333333333333333333333"),) * 5)
        self.assertAlmostEqual(float(result.returns.levered_irr), 0.264615, places=6)

    def test_requires_amortization_to_cover_the_hold_period(self) -> None:
        with self.assertRaisesRegex(ValueError, "amortization_years"):
            UnderwritingAssumptions(
                purchase_price=D("1000000"), closing_cost_rate=D("0.02"), loan_to_value=D("0.60"),
                annual_interest_rate=D("0"), amortization_years=4, exit_cap_rate=D("0.10"),
                selling_cost_rate=D("0.02"), operating=self.assumptions.operating,
            )
