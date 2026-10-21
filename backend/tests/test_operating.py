from decimal import Decimal
import unittest

from backend.engines.operating import OperatingAssumptions, project_monthly_operations, project_operations


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

    def test_projects_income_expenses_and_noi(self) -> None:
        projection = project_operations(self.assumptions)

        self.assertEqual(len(projection), 5)
        self.assertEqual(projection[0].potential_gross_income, D("103000.00"))
        self.assertEqual(projection[0].vacancy_loss, D("5150.0000"))
        self.assertEqual(projection[0].effective_gross_income, D("97850.0000"))
        self.assertEqual(projection[0].operating_expenses, D("30600.00"))
        self.assertEqual(projection[0].net_operating_income, D("67250.0000"))
        self.assertEqual(projection[1].net_operating_income, D("69573.500000"))
        self.assertEqual(projection[-1].year, 5)

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

        self.assertEqual([year.potential_gross_income for year in projection], [D("110000.00"), D("110000.00"), D("110000.00"), D("110000.00"), D("110000.00")])

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
