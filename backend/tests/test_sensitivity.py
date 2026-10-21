from dataclasses import replace
from decimal import Decimal
import unittest

from backend.engines.operating import OperatingAssumptions
from backend.workflows.sensitivity import SensitivityAssumptions, calculate_one_way_sensitivities
from backend.workflows.underwriting import UnderwritingAssumptions


D = Decimal


class SensitivityTests(unittest.TestCase):
    def setUp(self) -> None:
        underwriting = UnderwritingAssumptions(
            purchase_price=D("1000000"), closing_cost_rate=D("0.02"), loan_to_value=D("0.60"),
            annual_interest_rate=D("0.05"), amortization_years=30, exit_cap_rate=D("0.06"),
            selling_cost_rate=D("0.02"), operating=OperatingAssumptions(
                current_potential_gross_income=D("200000"), current_operating_expenses=D("50000"),
                vacancy_rate=D("0.05"), rent_growth_rate=D("0.03"), expense_growth_rate=D("0.02"), hold_period_years=5,
            ),
        )
        self.assumptions = SensitivityAssumptions(
            underwriting=underwriting, target_levered_irr=D("0.12"), minimum_dscr=D("1.20"),
            minimum_purchase_price=D("100000"), maximum_purchase_price=D("3000000"),
        )

    def test_returns_expected_one_way_price_directionality(self) -> None:
        result = calculate_one_way_sensitivities(self.assumptions)

        self.assertEqual([dimension.key for dimension in result.dimensions], ["rent_growth_rate", "exit_cap_rate", "annual_interest_rate"])
        rent, exit_cap, interest = result.dimensions
        self.assertEqual([point.value for point in rent.points], [D("0.02"), D("0.03"), D("0.04")])
        self.assertGreater(rent.points[2].maximum_purchase_price, rent.points[0].maximum_purchase_price)
        self.assertGreater(exit_cap.points[0].maximum_purchase_price, exit_cap.points[2].maximum_purchase_price)
        self.assertGreater(interest.points[0].maximum_purchase_price, interest.points[2].maximum_purchase_price)

    def test_clamps_zero_interest_rate_without_duplicate_scenario(self) -> None:
        zero_rate = replace(self.assumptions.underwriting, annual_interest_rate=D("0"))
        result = calculate_one_way_sensitivities(replace(self.assumptions, underwriting=zero_rate))

        self.assertEqual([point.value for point in result.dimensions[2].points], [D("0"), D("0.01")])

    def test_shifts_the_full_rent_growth_schedule_without_replacing_it(self) -> None:
        scheduled = replace(
            self.assumptions.underwriting,
            operating=replace(self.assumptions.underwriting.operating, annual_rent_growth_rates=(D("0.02"), D("0.03"))),
        )

        result = calculate_one_way_sensitivities(replace(self.assumptions, underwriting=scheduled))
        rent = result.dimensions[0]

        self.assertEqual(rent.label, "Rent-growth schedule")
        self.assertEqual([point.value for point in rent.points], [None, None, None])
        self.assertIn("every scheduled", rent.description)
        self.assertGreater(rent.points[2].maximum_purchase_price, rent.points[0].maximum_purchase_price)
