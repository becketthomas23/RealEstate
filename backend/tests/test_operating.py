from dataclasses import replace
from decimal import Decimal
import unittest

from backend.engines.operating import OperatingAssumptions, project_monthly_operations, project_operations, project_terminal_noi


D = Decimal


class OperatingEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assumptions = OperatingAssumptions(
            current_potential_gross_income=D("100000"),
            current_operating_expenses=D("30000"),
            vacancy_rate=D("0.05"),
            rent_growth_rate=D("0.03"),
            expense_growth_rate=D("0.02"),
            hold_period_years=5,
        )

    def test_year_one_equals_current_figures_and_growth_begins_in_year_two(self) -> None:
        projection = project_operations(self.assumptions)

        self.assertEqual(len(projection), 5)
        # Year 1 is the entered in-place year: 100,000 PGI, 5% vacancy, 30,000 expenses.
        self.assertEqual(projection[0].potential_gross_income, D("100000"))
        self.assertEqual(projection[0].vacancy_loss, D("5000.00"))
        self.assertEqual(projection[0].effective_gross_income, D("95000.00"))
        self.assertEqual(projection[0].operating_expenses, D("30000"))
        self.assertEqual(projection[0].net_operating_income, self.assumptions.current_noi)
        # Year 2 applies one growth step: 103,000 PGI and 30,600 expenses.
        self.assertEqual(projection[1].potential_gross_income, D("103000.00"))
        self.assertEqual(projection[1].net_operating_income, D("67250.0000"))
        self.assertEqual(projection[2].net_operating_income, D("69573.500000"))
        self.assertEqual(projection[-1].year, 5)

    def test_forward_convention_grows_once_before_year_one(self) -> None:
        forward = replace(self.assumptions, apply_growth_in_year_one=True)

        projection = project_operations(forward)

        self.assertEqual(projection[0].potential_gross_income, D("103000.00"))
        self.assertEqual(projection[0].operating_expenses, D("30600.00"))
        self.assertEqual(projection[0].net_operating_income, D("67250.0000"))
        self.assertEqual(project_terminal_noi(forward), D("100000") * D("1.03") ** 6 * D("0.95") - D("30000") * D("1.02") ** 6)

    def test_terminal_noi_is_the_year_after_the_hold(self) -> None:
        self.assertEqual(
            project_terminal_noi(self.assumptions),
            D("100000") * D("1.03") ** 5 * D("0.95") - D("30000") * D("1.02") ** 5,
        )

    def test_current_noi_is_calculated_from_the_same_definition(self) -> None:
        self.assertEqual(self.assumptions.current_noi, D("65000.00"))

    def test_rejects_invalid_assumptions(self) -> None:
        with self.assertRaisesRegex(ValueError, "vacancy_rate"):
            OperatingAssumptions(D("100"), D("20"), D("1"), D("0.03"), D("0.02"), 5)
        with self.assertRaisesRegex(ValueError, "hold_period_years"):
            OperatingAssumptions(D("100"), D("20"), D("0.05"), D("0.03"), D("0.02"), 4)

    def test_allows_negative_noi_when_expenses_exceed_effective_income(self) -> None:
        assumptions = OperatingAssumptions(D("100"), D("200"), D("0.05"), D("0"), D("0"), 5)

        self.assertEqual(project_operations(assumptions)[0].net_operating_income, D("-105.00"))

    def test_rent_growth_schedule_overrides_the_base_rate_and_continues_last_rate(self) -> None:
        assumptions = OperatingAssumptions(
            D("100000"), D("30000"), D("0.05"), D("0.03"), D("0.02"), 5,
            annual_rent_growth_rates=(D("0.10"), D("0")),
        )

        projection = project_operations(assumptions)

        # The schedule's first rate applies to the first growth year (Year 2).
        self.assertEqual([year.potential_gross_income for year in projection], [D("100000"), D("110000.00"), D("110000.00"), D("110000.00"), D("110000.00")])

    def test_monthly_projection_reconciles_to_annual_projection(self) -> None:
        annual = project_operations(self.assumptions)
        monthly = project_monthly_operations(self.assumptions)

        self.assertEqual(len(monthly), 60)
        self.assertEqual(monthly[0].month, 1)
        self.assertEqual(monthly[-1].month, 60)
        for year in annual:
            months = [item for item in monthly if item.year == year.year]
            self.assertEqual(sum(item.net_operating_income for item in months), year.net_operating_income)


if __name__ == "__main__":
    unittest.main()
