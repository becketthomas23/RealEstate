from decimal import Decimal
import unittest

from backend.engines.waterfall import WaterfallAssumptions, calculate_waterfall


D = Decimal


class WaterfallTests(unittest.TestCase):
    def test_returns_capital_then_pref_then_splits_residual(self) -> None:
        result = calculate_waterfall(
            WaterfallAssumptions(
                initial_lp_equity=D("100"),
                annual_property_cash_flows=(D("20"), D("200")),
                preferred_return_rate=D("0.10"),
                sponsor_residual_share=D("0.20"),
            )
        )

        first, second = result.years
        self.assertEqual(first.return_of_capital_to_lp, D("20"))
        self.assertEqual(second.return_of_capital_to_lp, D("80"))
        self.assertEqual(second.preferred_return_to_lp, D("18"))
        self.assertEqual(second.residual_to_sponsor, D("20.40"))
        self.assertEqual(result.total_sponsor_distributed, D("20.40"))

    def test_negative_cash_flow_is_an_lp_capital_call(self) -> None:
        result = calculate_waterfall(
            WaterfallAssumptions(D("100"), (D("-25"), D("200")), D("0.08"), D("0.20"))
        )

        self.assertEqual(result.years[0].lp_capital_contribution, D("25"))
        self.assertEqual(result.total_lp_contributed, D("125"))
        self.assertEqual(result.total_lp_distributed, D("187.00"))
        self.assertEqual(result.lp_equity_multiple, D("1.496"))
