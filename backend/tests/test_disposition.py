from decimal import Decimal
import unittest
from backend.engines.disposition import DispositionAssumptions, calculate_disposition

class DispositionEngineTests(unittest.TestCase):
    def test_calculates_sale_proceeds(self) -> None:
        result = calculate_disposition(DispositionAssumptions(Decimal("100000"), Decimal("0.05"), Decimal("0.02"), Decimal("800000")))
        self.assertEqual(result.gross_sale_price, Decimal("2000000"))
        self.assertEqual(result.net_sale_proceeds_to_equity, Decimal("1160000.00"))
