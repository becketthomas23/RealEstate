from decimal import Decimal
import unittest

from backend.engines.debt import DebtAssumptions, project_debt, project_monthly_debt


D = Decimal


class DebtEngineTests(unittest.TestCase):
    def test_projects_standard_monthly_fixed_rate_amortization(self) -> None:
        assumptions = DebtAssumptions(D("100000"), D("0.05"), 30, 5)
        monthly = project_monthly_debt(assumptions)
        projection = project_debt(assumptions)

        self.assertEqual(len(monthly), 60)
        self.assertEqual(monthly[0].interest, D("416.6666666666666666666666667"))
        self.assertEqual(monthly[0].debt_service.quantize(D(".01")), D("536.82"))
        self.assertEqual(monthly[11].ending_balance.quantize(D(".01")), D("98524.63"))
        self.assertEqual(projection[0].debt_service, sum((month.debt_service for month in monthly[:12]), D("0")))
        self.assertEqual(projection[0].principal, sum((month.principal for month in monthly[:12]), D("0")))
        self.assertEqual(projection[0].ending_balance, monthly[11].ending_balance)

    def test_zero_rate_monthly_schedule_fully_amortizes(self) -> None:
        assumptions = DebtAssumptions(D("120000"), D("0"), 5, 5)
        monthly = project_monthly_debt(assumptions)
        projection = project_debt(assumptions)

        self.assertEqual(monthly[0].debt_service, D("2000"))
        self.assertEqual(projection[0].debt_service, D("24000"))
        self.assertEqual(monthly[-1].ending_balance, D("0"))
        self.assertEqual(projection[-1].ending_balance, D("0"))

    def test_rejects_hold_period_outside_product_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "hold_period_years"):
            DebtAssumptions(D("100000"), D("0.05"), 30, 4)

    def test_requires_amortization_to_cover_hold_period(self) -> None:
        with self.assertRaisesRegex(ValueError, "amortization_years"):
            DebtAssumptions(D("100000"), D("0.05"), 4, 5)
