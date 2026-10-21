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
        self.assertEqual(result.going_in_cap_rate, D("0.1300"))
        self.assertEqual(result.debt_yield, D("0.2166666666666666666666666667"))
        self.assertEqual(len(result.monthly_operating_projection), 60)
        self.assertEqual(sum(item.net_operating_income for item in result.monthly_operating_projection[:12]), D("130000.00"))
        self.assertEqual(result.debt_projection[0].debt_service, D("120000"))
        self.assertEqual(result.terminal_noi, D("130000.00"))
        self.assertEqual(result.disposition.gross_sale_price, D("1300000.0"))
        self.assertEqual(result.disposition.net_sale_proceeds_to_equity, D("1274000.000"))
        self.assertEqual(result.annual_operating_cash_flows, (D("10000.00"),) * 5)
        self.assertEqual(result.annual_cash_flows, (D("10000.00"),) * 4 + (D("1284000.000"),))
        self.assertEqual(result.returns.cash_on_cash_by_year, (D("0.02380952380952380952380952381"),) * 5)
        self.assertEqual(result.returns.dscr_by_year, (D("1.083333333333333333333333333"),) * 5)
        self.assertAlmostEqual(float(result.returns.levered_irr), 0.264615, places=6)
        self.assertEqual([flag.code for flag in result.risk_flags], ["thin_dscr", "exit_cap_compression"])
        self.assertEqual(result.risk_flags[0].threshold, D("1.20"))

    def test_requires_amortization_to_cover_the_hold_period(self) -> None:
        with self.assertRaisesRegex(ValueError, "amortization_years"):
            UnderwritingAssumptions(
                purchase_price=D("1000000"), closing_cost_rate=D("0.02"), loan_to_value=D("0.60"),
                annual_interest_rate=D("0"), amortization_years=4, exit_cap_rate=D("0.10"),
                selling_cost_rate=D("0.02"), operating=self.assumptions.operating,
            )

    def test_all_cash_deal_has_no_debt_metrics_or_payoff(self) -> None:
        all_cash = UnderwritingAssumptions(
            purchase_price=D("1000000"), closing_cost_rate=D("0.02"), loan_to_value=D("0"),
            annual_interest_rate=D("0.05"), amortization_years=30, exit_cap_rate=D("0.10"),
            selling_cost_rate=D("0.02"), operating=self.assumptions.operating,
        )

        result = calculate_underwriting(all_cash)

        self.assertEqual(all_cash.initial_equity, D("1020000.00"))
        self.assertTrue(all(year.debt_service == D("0") and year.ending_balance == D("0") for year in result.debt_projection))
        self.assertIsNone(result.debt_yield)
        self.assertIsNone(result.returns.minimum_dscr)
        self.assertEqual(result.disposition.loan_payoff, D("0"))
        self.assertEqual(result.annual_operating_cash_flows, (D("130000.00"),) * 5)
