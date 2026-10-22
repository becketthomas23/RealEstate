from decimal import Decimal
import unittest

from backend.engines.operating import OperatingAssumptions
from backend.workflows.sensitivity import (
    AdvancedSensitivityAssumptions,
    AdvancedSensitivityDimension,
    calculate_advanced_sensitivity,
)
from backend.workflows.underwriting import UnderwritingAssumptions


D = Decimal


class AdvancedSensitivityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.underwriting = UnderwritingAssumptions(
            purchase_price=D("1000000"), closing_cost_rate=D("0.02"), loan_to_value=D("0.60"),
            annual_interest_rate=D("0.05"), amortization_years=30, exit_cap_rate=D("0.06"),
            selling_cost_rate=D("0.02"), operating=OperatingAssumptions(
                current_potential_gross_income=D("200000"), current_operating_expenses=D("50000"),
                vacancy_rate=D("0.05"), rent_growth_rate=D("0.03"), expense_growth_rate=D("0.02"), hold_period_years=5,
            ),
        )

    def test_calculates_every_mixed_three_variable_scenario(self) -> None:
        result = calculate_advanced_sensitivity(
            AdvancedSensitivityAssumptions(
                underwriting=self.underwriting,
                dimensions=(
                    AdvancedSensitivityDimension("rent_growth_rate", (D("0.02"), D("0.04"))),
                    AdvancedSensitivityDimension("exit_cap_rate", (D("0.05"), D("0.07"))),
                    AdvancedSensitivityDimension("vacancy_rate", (D("0.04"), D("0.06"))),
                ),
            )
        )

        self.assertEqual(len(result.scenarios), 8)
        self.assertEqual(result.scenarios[0].values, {"rent_growth_rate": D("0.02"), "exit_cap_rate": D("0.05"), "vacancy_rate": D("0.04")})
        self.assertTrue(all(scenario.metric_value is not None for scenario in result.scenarios))
        self.assertGreater(result.scenarios[0].metric_value, result.scenarios[-1].metric_value)

    def test_rejects_duplicate_dimensions(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            AdvancedSensitivityAssumptions(
                self.underwriting,
                (
                    AdvancedSensitivityDimension("vacancy_rate", (D("0.04"), D("0.05"))),
                    AdvancedSensitivityDimension("vacancy_rate", (D("0.05"), D("0.06"))),
                ),
            )

    def test_rent_growth_grid_keeps_the_shape_of_a_scheduled_case(self) -> None:
        from dataclasses import replace

        scheduled = replace(
            self.underwriting,
            operating=replace(self.underwriting.operating, annual_rent_growth_rates=(D("0.06"), D("0.03"))),
        )

        flat = calculate_advanced_sensitivity(
            AdvancedSensitivityAssumptions(self.underwriting, (AdvancedSensitivityDimension("rent_growth_rate", (D("0.03"), D("0.04"))),))
        )
        shaped = calculate_advanced_sensitivity(
            AdvancedSensitivityAssumptions(scheduled, (AdvancedSensitivityDimension("rent_growth_rate", (D("0.03"), D("0.04"))),))
        )

        # The scheduled case has higher early growth, so its IRR must stay above the flat case
        # in every scenario instead of collapsing onto the flat case's numbers.
        for flat_case, shaped_case in zip(flat.scenarios, shaped.scenarios, strict=True):
            self.assertGreater(shaped_case.metric_value, flat_case.metric_value)
