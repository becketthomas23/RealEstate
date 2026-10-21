from decimal import Decimal
import unittest
from backend.engines.returns import ReturnAssumptions, calculate_returns

class ReturnEngineTests(unittest.TestCase):
    def test_calculates_return_metrics_without_other_engines(self) -> None:
        metrics = calculate_returns(ReturnAssumptions(Decimal("100"), (Decimal("60"), Decimal("60")), (Decimal("120"), Decimal("130")), (Decimal("100"), Decimal("100"))))
        self.assertEqual(metrics.equity_multiple, Decimal("1.2"))
        self.assertEqual(metrics.total_equity_contributed, Decimal("100"))
        self.assertEqual(metrics.total_equity_distributed, Decimal("120"))
        self.assertEqual(metrics.cash_on_cash_by_year, (Decimal("0.6"), Decimal("0.6")))
        self.assertEqual(metrics.dscr_by_year, (Decimal("1.2"), Decimal("1.3")))
        self.assertAlmostEqual(float(metrics.levered_irr), 0.1306623863, places=8)

    def test_equity_multiple_includes_follow_on_equity_for_negative_cash_flow(self) -> None:
        metrics = calculate_returns(ReturnAssumptions(Decimal("100"), (Decimal("-20"), Decimal("180"))))

        self.assertEqual(metrics.total_equity_contributed, Decimal("120"))
        self.assertEqual(metrics.total_equity_distributed, Decimal("180"))
        self.assertEqual(metrics.equity_multiple, Decimal("1.5"))

    def test_cash_on_cash_excludes_terminal_sale_proceeds_when_operating_cash_flow_is_supplied(self) -> None:
        metrics = calculate_returns(
            ReturnAssumptions(
                Decimal("100"),
                (Decimal("8"), Decimal("158")),
                annual_operating_cash_flows=(Decimal("8"), Decimal("8")),
            )
        )

        self.assertEqual(metrics.cash_on_cash_by_year, (Decimal("0.08"), Decimal("0.08")))

    def test_rejects_an_ambiguous_irr_with_multiple_valid_roots(self) -> None:
        # -100, +230, -132 has valid roots at 10% and 20%.
        with self.assertRaisesRegex(ValueError, "multiple valid IRRs"):
            calculate_returns(ReturnAssumptions(Decimal("100"), (Decimal("230"), Decimal("-132"))))
