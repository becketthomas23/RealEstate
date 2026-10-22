from dataclasses import replace
from decimal import Decimal
import unittest

from backend.engines.operating import OperatingAssumptions
from backend.workflows.monte_carlo import Correlation, MonteCarloAssumptions, SimulationVariable, calculate_monte_carlo
from backend.workflows.monte_carlo.calibration import _parse_rate, calculate_market_calibration
from backend.workflows.monte_carlo.calculator import _draw, sampled_range
from backend.workflows.underwriting import UnderwritingAssumptions
from backend.workflows.underwriting.scenarios import apply_scenario_values


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

    def test_seeded_runs_are_reproducible_and_report_full_statistics(self) -> None:
        assumptions = MonteCarloAssumptions(
            underwriting=self.underwriting,
            variables=(
                SimulationVariable("rent_growth_rate", "medium", D("50")),
                SimulationVariable("exit_cap_rate", "high", D("80")),
                SimulationVariable("vacancy_rate", "low", D("20")),
            ),
            iterations=200,
            seed=42,
            target_levered_irr=D("0.12"),
            minimum_dscr=D("1.25"),
        )

        first = calculate_monte_carlo(assumptions)
        second = calculate_monte_carlo(assumptions)

        self.assertEqual(first, second)
        irr = first.levered_irr
        self.assertLessEqual(irr.minimum, irr.percentile_5)
        self.assertLessEqual(irr.percentile_5, irr.percentile_25)
        self.assertLessEqual(irr.percentile_25, irr.percentile_50)
        self.assertLessEqual(irr.percentile_50, irr.percentile_75)
        self.assertLessEqual(irr.percentile_75, irr.percentile_95)
        self.assertLessEqual(irr.percentile_95, irr.maximum)
        self.assertGreater(irr.standard_deviation, D("0"))
        self.assertTrue(D("0") <= irr.probability_meeting_target <= D("1"))
        self.assertEqual(sum(item.count for item in first.irr_histogram), 200)
        self.assertEqual(first.irr_histogram[0].lower, irr.minimum)
        self.assertEqual(first.irr_histogram[-1].upper, irr.maximum)
        self.assertTrue(D("0") <= first.probability_of_loss <= D("1"))
        self.assertIsNotNone(first.minimum_dscr)
        self.assertTrue(D("0") <= first.probability_dscr_below_floor <= D("1"))
        self.assertEqual(len(first.sampled_ranges), 3)
        self.assertEqual(first.sampled_ranges[0].distribution, "triangular")
        self.assertLessEqual(first.downside_case.levered_irr, first.upside_case.levered_irr)
        self.assertEqual(set(first.downside_case.values), {"rent_growth_rate", "exit_cap_rate", "vacancy_rate"})
        from backend.workflows.underwriting import calculate_underwriting

        self.assertEqual(first.base_case_irr, calculate_underwriting(self.underwriting).returns.levered_irr)

    def test_rejects_incomplete_manual_range_and_mode_outside_it(self) -> None:
        with self.assertRaisesRegex(ValueError, "together"):
            SimulationVariable("rent_growth_rate", "medium", D("50"), minimum=D("0"))
        with self.assertRaisesRegex(ValueError, "mode"):
            SimulationVariable("rent_growth_rate", "medium", D("50"), minimum=D("0.01"), maximum=D("0.05"), mode=D("0.09"))
        with self.assertRaisesRegex(ValueError, "distribution"):
            SimulationVariable("rent_growth_rate", "medium", D("50"), distribution="lognormal")

    def test_low_confidence_produces_a_wider_automatic_range_than_high_confidence(self) -> None:
        base = D("0.03")
        low = sampled_range(SimulationVariable("rent_growth_rate", "low", D("50")), base)
        high = sampled_range(SimulationVariable("rent_growth_rate", "high", D("50")), base)

        self.assertGreater(low.maximum - low.minimum, high.maximum - high.minimum)
        self.assertEqual(low.mode, base)

    def test_marginal_distributions_stay_inside_the_band_and_centre_on_the_mode(self) -> None:
        band = sampled_range(SimulationVariable("exit_cap_rate", "medium", D("50"), minimum=D("0.05"), maximum=D("0.08"), mode=D("0.06")), D("0.06"))
        for distribution in ("uniform", "triangular", "normal"):
            shaped = replace(band, distribution=distribution)
            draws = [_draw(shaped, (index + 0.5) / 1000) for index in range(1000)]
            self.assertGreaterEqual(min(draws), D("0.05"))
            self.assertLessEqual(max(draws), D("0.08"))
            median = sorted(draws)[500]
            if distribution == "uniform":
                expected = D("0.065")  # band midpoint
            elif distribution == "triangular":
                # Analytical median of a triangular distribution with the mode below the midpoint.
                expected = D("0.05") + (D("0.5") * D("0.03") * D("0.01")).sqrt()
            else:
                expected = D("0.06")  # truncated normal centred on the mode
            self.assertLess(abs(median - expected), D("0.0025"), distribution)

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
        self.assertIsNone(result.probability_dscr_below_floor)

    def test_driver_impacts_quantify_cash_flow_irr_and_tornado_ends(self) -> None:
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
        self.assertGreater(impacts["rent_growth_rate"].irr_at_high, impacts["rent_growth_rate"].irr_at_low)
        # Exit cap changes terminal value and IRR, but not recurring cash flow.
        self.assertEqual(impacts["exit_cap_rate"].cash_flow_change_per_100_bps, D("0"))
        self.assertLess(impacts["exit_cap_rate"].irr_change_per_100_bps, D("0"))
        self.assertLess(impacts["exit_cap_rate"].irr_at_high, impacts["exit_cap_rate"].irr_at_low)
        self.assertLess(impacts["exit_cap_rate"].sampled_low, impacts["exit_cap_rate"].sampled_high)

    def test_rent_growth_schedule_is_shifted_rather_than_replaced(self) -> None:
        scheduled = replace(
            self.underwriting,
            operating=replace(self.underwriting.operating, annual_rent_growth_rates=(D("0.05"), D("0.04"), D("0.02"))),
        )

        scenario = apply_scenario_values(scheduled, {"rent_growth_rate": D("0.02")})

        # A 2% case is 100 bps below the 3% base, so every scheduled year moves down 100 bps.
        self.assertEqual(scenario.operating.annual_rent_growth_rates, (D("0.04"), D("0.03"), D("0.01")))
        self.assertEqual(scenario.operating.rent_growth_rate, D("0.02"))
        result = calculate_monte_carlo(
            MonteCarloAssumptions(
                underwriting=scheduled,
                variables=(SimulationVariable("rent_growth_rate", "medium", D("50")),),
                iterations=100,
                seed=3,
            )
        )
        self.assertEqual(result.iterations, 100)

    def test_market_calibration_calculates_all_driver_pairs(self) -> None:
        rows = [
            f"202{year}-Q1,Multifamily,$10M-$25M,{0.02 + year / 1000:.3f},{0.060 - year / 1000:.3f},{0.07 - year / 2000:.3f},{0.02 + year / 1500:.3f},{0.04 + year / 1200:.3f}"
            for year in range(8)
        ]
        csv = (
            "period,property_type,value_bucket,rent_growth_rate,exit_cap_rate,vacancy_rate,expense_growth_rate,annual_interest_rate\n"
            + "\n".join(rows)
        ).encode()

        calibration = calculate_market_calibration(
            csv, "Multifamily", "$10M-$25M", "Synthetic test market history", "2026-10-21"
        )

        self.assertEqual(calibration.context.observations, 8)
        self.assertEqual(calibration.context.source_as_of_date, "2026-10-21")
        self.assertEqual(len(calibration.correlations), 10)
        self.assertEqual(len(calibration.driver_ranges), 5)
        self.assertLessEqual(calibration.driver_ranges[0].percentile_10, calibration.driver_ranges[0].percentile_50)
        self.assertLessEqual(calibration.driver_ranges[0].percentile_50, calibration.driver_ranges[0].percentile_90)
        self.assertEqual(len(calibration.warnings), 1)

    def test_market_calibration_accepts_percent_formatted_rates(self) -> None:
        self.assertEqual(_parse_rate("5.25%"), D("0.0525"))
        self.assertEqual(_parse_rate("0.0525"), D("0.0525"))
