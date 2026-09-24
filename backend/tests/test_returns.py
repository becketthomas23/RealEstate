from decimal import Decimal
import unittest
from backend.engines.returns import ReturnAssumptions, calculate_returns

class ReturnEngineTests(unittest.TestCase):
    def test_calculates_return_metrics_without_other_engines(self) -> None:
        metrics = calculate_returns(ReturnAssumptions(Decimal("100"), (Decimal("60"), Decimal("60")), (Decimal("120"), Decimal("130")), (Decimal("100"), Decimal("100"))))
        self.assertEqual(metrics.equity_multiple, Decimal("1.2"))
        self.assertEqual(metrics.dscr_by_year, (Decimal("1.2"), Decimal("1.3")))
        self.assertAlmostEqual(float(metrics.levered_irr), 0.1306623863, places=8)
