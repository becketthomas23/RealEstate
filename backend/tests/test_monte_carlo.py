from decimal import Decimal
import unittest

from backend.engines.operating import OperatingAssumptions
from backend.workflows.monte_carlo import Correlation, MonteCarloAssumptions, SimulationVariable, calculate_monte_carlo
from backend.workflows.monte_carlo.calibration import _parse_rate, calculate_market_calibration
from backend.workflows.monte_carlo.calculator import _sample
from random import Random
from backend.workflows.underwriting import UnderwritingAssumptions


D = Decimal


class MonteCarloTests(unittest.TestCase):
    def setUp(self) -> None:
        self.underwriting = UnderwritingAssumptions(
            purchase_price=D("1000000"), closing_cost_rate=D("0.02"), loan_to_value=D("0.60"),
            annual_interest_rate=D("0.05"), amortization_years=30, exit_cap_rate=D("0.06"),
            selling_cost_rate=D("0.02"), operating=OperatingAssumptions(
                current_potential_gross_income=D("200000"), current_operating_expenses=D("50000"),
                vacancy_rate=D("0.05"), rent_growth_rate=D("0.03"), expense_growth_rate=D("0.02"), hold_period_years=5,
            ),
        )

    def test_seeded_runs_are_reproducible_and_include_target_probability(self) -> None:
        assumptions = MonteCarloAssumptions(
            underwriting=self.underwriting,
            variables=(
                SimulationVariable("rent_growth_rate", "medium", D("50")),
                SimulationVariable("exit_cap_rate", "high", D("80")),
                SimulationVariable("vacancy_rate", "low", D("20")),
            ),
            iterations=100,
            seed=42,
            target_levered_irr=D("0.12"),
        )

        first = calculate_monte_carlo(assumptions)
        second = calculate_monte_carlo(assumptions)

        self.assertEqual(first, second)
        self.assertGreaterEqual(first.levered_irr.probability_meeting_target, D("0"))
        self.assertLessEqual(first.levered_irr.probability_meeting_target, D("1"))
        self.assertLessEqual(first.levered_irr.percentile_10, first.levered_irr.percentile_50)
        self.assertLessEqual(first.levered_irr.percentile_50, first.levered_irr.percentile_90)
        self.assertLessEqual(first.downside_case.levered_irr, first.upside_case.levered_irr)
        self.assertEqual(set(first.downside_case.values), {"rent_growth_rate", "exit_cap_rate", "vacancy_rate"})

    def test_rejects_incomplete_manual_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "together"):
            SimulationVariable("rent_growth_rate", "medium", D("50"), minimum=D("0"))

    def test_low_confidence_produces_a_wider_automatic_range_than_high_confidence(self) -> None:
        base = D("0.03")
        low = _sample(SimulationVariable("rent_growth_rate", "low", D("50")), base, Random(1))
        high = _sample(SimulationVariable("rent_growth_rate", "high", D("50")), base, Random(1))

        self.assertGreater(abs(low - base), abs(high - base))

    def test_correlated_drivers_are_saved_with_ranked_return_associations(self) -> None:
        result = calculate_monte_carlo(
            MonteCarloAssumptions(
                underwriting=self.underwriting,
                variables=(
                    SimulationVariable("rent_growth_rate", "medium", D("50")),
                    SimulationVariable("vacancy_rate", "medium", D("50")),
                ),
                correlations=(Correlation("rent_growth_rate", "vacancy_rate", D("-0.60")),),
                iterations=100,
                seed=42,
            )
        )

        self.assertEqual(result.correlations[0].coefficient, D("-0.60"))
        self.assertEqual({impact.key for impact in result.driver_impacts}, {"rent_growth_rate", "vacancy_rate"})
        self.assertEqual(sum(impact.relative_influence for impact in result.driver_impacts).quantize(D("0.0001")), D("1.0000"))

    def test_driver_impacts_quantify_cash_flow_and_irr_change_per_100_bps(self) -> None:
        result = calculate_monte_carlo(
            MonteCarloAssumptions(
                underwriting=self.underwriting,
                variables=(
                    SimulationVariable("rent_growth_rate", "medium", D("50")),
                    SimulationVariable("exit_cap_rate", "medium", D("50")),
                ),
                iterations=100,
                seed=42,
            )
        )

        impacts = {impact.key: impact for impact in result.driver_impacts}
        self.assertGreater(impacts["rent_growth_rate"].cash_flow_change_per_100_bps, D("0"))
        self.assertGreater(impacts["rent_growth_rate"].irr_change_per_100_bps, D("0"))
        # Exit cap changes terminal value and IRR, but not recurring cash flow.
        self.assertEqual(impacts["exit_cap_rate"].cash_flow_change_per_100_bps, D("0"))
        # Its joint-simulation cash-flow correlation can be nonzero because
        # the selected rent-growth draws vary in the same finite sample. The
        # controlled cash-flow effect above remains exactly zero.
        self.assertLess(impacts["exit_cap_rate"].irr_change_per_100_bps, D("0"))

    def test_market_calibration_calculates_all_driver_pairs(self) -> None:
        rows = [
            f"202{year}-Q1,Multifamily,$10M-$25M,{0.02 + year / 1000:.3f},{0.060 - year / 1000:.3f},{0.07 - year / 2000:.3f},{0.02 + year / 1500:.3f},{0.04 + year / 1200:.3f}"
            for year in range(8)
        ]
        csv = (
            "period,property_type,value_bucket,rent_growth_rate,exit_cap_rate,vacancy_rate,expense_growth_rate,annual_interest_rate\n"
            + "\n".join(rows)
        ).encode()

        calibration = calculate_market_calibration(csv, "Multifamily", "$10M-$25M", "Educational CoStar export")

        self.assertEqual(calibration.context.observations, 8)
        self.assertEqual(len(calibration.correlations), 10)
        self.assertEqual(len(calibration.driver_ranges), 5)
        self.assertLessEqual(calibration.driver_ranges[0].percentile_10, calibration.driver_ranges[0].percentile_50)
        self.assertLessEqual(calibration.driver_ranges[0].percentile_50, calibration.driver_ranges[0].percentile_90)
        self.assertEqual(len(calibration.warnings), 1)

    def test_market_calibration_accepts_percent_formatted_rates(self) -> None:
        self.assertEqual(_parse_rate("5.25%"), D("0.0525"))
        self.assertEqual(_parse_rate("0.0525"), D("0.0525"))
