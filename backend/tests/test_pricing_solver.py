from dataclasses import replace
from decimal import Decimal
import unittest

from backend.engines.operating import OperatingAssumptions
from backend.solvers.pricing import MaximumPriceAssumptions, solve_maximum_purchase_price
from backend.workflows.underwriting import UnderwritingAssumptions


D = Decimal


class MaximumPriceSolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.underwriting = UnderwritingAssumptions(
            purchase_price=D("1000000"), closing_cost_rate=D("0.02"), loan_to_value=D("0.60"),
            annual_interest_rate=D("0"), amortization_years=5, exit_cap_rate=D("0.10"), selling_cost_rate=D("0.02"),
            operating=OperatingAssumptions(D("200000"), D("50000"), D("0.10"), D("0"), D("0"), 5),
        )

    def test_finds_maximum_price_when_dscr_is_binding(self) -> None:
        result = solve_maximum_purchase_price(
            MaximumPriceAssumptions(
                underwriting=self.underwriting,
                target_levered_irr=D("0.10"),
                minimum_dscr=D("1.00"),
                minimum_purchase_price=D("500000"),
                maximum_purchase_price=D("1500000"),
            )
        )

        # NOI 130,000 / (0.60 x price / 5 years) = 1.00 at price 1,083,333.33.
        self.assertAlmostEqual(float(result.maximum_purchase_price), 1083333.33, places=2)
        self.assertEqual(result.binding_constraint, "minimum_dscr")
        self.assertEqual(result.recommended_bid_floor, result.maximum_purchase_price * D("0.95"))
        self.assertEqual(result.recommended_bid_ceiling, result.maximum_purchase_price)
        self.assertGreaterEqual(result.underwriting.returns.levered_irr, D("0.10"))
        self.assertGreaterEqual(result.underwriting.returns.minimum_dscr, D("1.00"))
        self.assertEqual(result.underwriting.purchase_price, result.maximum_purchase_price)

    def test_brackets_automatically_from_the_reference_price(self) -> None:
        explicit = solve_maximum_purchase_price(
            MaximumPriceAssumptions(self.underwriting, D("0.10"), D("1.00"), D("500000"), D("1500000"))
        )

        # Reference price below the answer: the solver expands upward.
        from_below = solve_maximum_purchase_price(MaximumPriceAssumptions(self.underwriting, D("0.10"), D("1.00")))
        # Reference price far above the answer: the solver contracts downward.
        from_above = solve_maximum_purchase_price(
            MaximumPriceAssumptions(replace(self.underwriting, purchase_price=D("50000000")), D("0.10"), D("1.00"))
        )

        for result in (from_below, from_above):
            self.assertLessEqual(abs(result.maximum_purchase_price - explicit.maximum_purchase_price), D("0.02"))
        self.assertLess(from_below.searched_minimum_price, from_below.maximum_purchase_price)
        self.assertGreater(from_below.searched_maximum_price, from_below.maximum_purchase_price)

    def test_reports_the_irr_as_binding_when_coverage_is_loose(self) -> None:
        result = solve_maximum_purchase_price(MaximumPriceAssumptions(self.underwriting, D("0.10"), D("0.50")))

        self.assertEqual(result.binding_constraint, "target_levered_irr")
        self.assertLess(abs(result.underwriting.returns.levered_irr - D("0.10")), D("0.001"))

    def test_requires_a_bracketed_price_range_when_bounds_are_explicit(self) -> None:
        assumptions = MaximumPriceAssumptions(
            underwriting=self.underwriting, target_levered_irr=D("0.10"), minimum_dscr=D("0.50"),
            minimum_purchase_price=D("500000"), maximum_purchase_price=D("600000"),
        )

        with self.assertRaisesRegex(ValueError, "higher bound"):
            solve_maximum_purchase_price(assumptions)

    def test_accepts_a_high_return_target_but_rejects_an_invalid_irr_floor(self) -> None:
        high_target = MaximumPriceAssumptions(
            underwriting=self.underwriting, target_levered_irr=D("1.50"), minimum_dscr=D("1.00"),
            minimum_purchase_price=D("500000"), maximum_purchase_price=D("1500000"),
        )

        self.assertEqual(high_target.target_levered_irr, D("1.50"))
        with self.assertRaisesRegex(ValueError, "greater than -1"):
            MaximumPriceAssumptions(
                underwriting=self.underwriting, target_levered_irr=D("-1"), minimum_dscr=D("1.00"),
                minimum_purchase_price=D("500000"), maximum_purchase_price=D("1500000"),
            )
