from decimal import Decimal
import unittest

from backend.engines.waterfall import WaterfallAssumptions, calculate_waterfall


D = Decimal


class WaterfallTests(unittest.TestCase):
    def test_pays_accrued_pref_then_capital_then_splits_residual(self) -> None:
        result = calculate_waterfall(
            WaterfallAssumptions(
                initial_lp_equity=D("100"),
                annual_property_cash_flows=(D("20"), D("200")),
                preferred_return_rate=D("0.10"),
                sponsor_residual_share=D("0.20"),
            )
        )

        first, second = result.years
        # Year 1: 10 accrues on 100; 10 pays the pref and 10 returns capital.
        self.assertEqual(first.accrued_preferred_return, D("10.00"))
        self.assertEqual(first.preferred_return_to_lp, D("10.00"))
        self.assertEqual(first.return_of_capital_to_lp, D("10.00"))
        self.assertEqual(first.unreturned_lp_capital, D("90.00"))
        # Year 2: 9 accrues on 90; 9 pref + 90 capital leaves 101 to split 80/20.
        self.assertEqual(second.accrued_preferred_return, D("9.0000"))
        self.assertEqual(second.preferred_return_to_lp, D("9.0000"))
        self.assertEqual(second.return_of_capital_to_lp, D("90.00"))
        self.assertEqual(second.residual_to_sponsor, D("20.200000"))
        self.assertEqual(result.total_sponsor_distributed, D("20.200000"))
        self.assertTrue(result.pay_preferred_return_before_capital)

    def test_return_of_capital_first_is_an_explicit_option(self) -> None:
        result = calculate_waterfall(
            WaterfallAssumptions(D("100"), (D("20"), D("200")), D("0.10"), D("0.20"), pay_preferred_return_before_capital=False)
        )

        first, second = result.years
        # Capital first: year 1 pays 20 of capital and leaves the 10 pref unpaid.
        self.assertEqual(first.return_of_capital_to_lp, D("20"))
        self.assertEqual(first.unpaid_preferred_return, D("10.00"))
        # Year 2 accrues 8 on the remaining 80, so 18 of pref is paid.
        self.assertEqual(second.return_of_capital_to_lp, D("80"))
        self.assertEqual(second.preferred_return_to_lp, D("18.0000"))
        self.assertEqual(result.total_sponsor_distributed, D("20.400000"))

    def test_pref_accrues_during_a_capital_call_year(self) -> None:
        result = calculate_waterfall(
            WaterfallAssumptions(D("100"), (D("-25"), D("200")), D("0.08"), D("0.20"))
        )

        call_year, exit_year = result.years
        self.assertEqual(call_year.lp_capital_contribution, D("25"))
        # 8% on the 100 of capital outstanding at the start of the call year.
        self.assertEqual(call_year.accrued_preferred_return, D("8.00"))
        self.assertEqual(call_year.unpaid_preferred_return, D("8.00"))
        self.assertEqual(call_year.unreturned_lp_capital, D("125"))
        # Year 2 adds 8% on 125, so 18 of pref is paid before 125 of capital.
        self.assertEqual(exit_year.preferred_return_to_lp, D("18.00"))
        self.assertEqual(exit_year.return_of_capital_to_lp, D("125"))
        self.assertEqual(exit_year.residual_to_sponsor, D("11.400"))
        self.assertEqual(result.total_lp_contributed, D("125"))
        self.assertEqual(result.total_lp_distributed, D("188.600"))
        self.assertEqual(result.lp_equity_multiple, D("1.5088"))

    def test_unpaid_pref_carries_forward_without_compounding(self) -> None:
        result = calculate_waterfall(
            WaterfallAssumptions(D("100"), (D("0"), D("0"), D("300")), D("0.10"), D("0.20"))
        )

        self.assertEqual([year.unpaid_preferred_return for year in result.years][:2], [D("10.00"), D("20.00")])
        self.assertEqual(result.years[2].preferred_return_to_lp, D("30.00"))
