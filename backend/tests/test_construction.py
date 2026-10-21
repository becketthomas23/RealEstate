from decimal import Decimal
import unittest

from backend.engines.construction import ConstructionLoanAssumptions, project_construction_loan


D = Decimal


class ConstructionLoanTests(unittest.TestCase):
    def test_projects_draws_equity_fees_and_capitalized_interest(self) -> None:
        result = project_construction_loan(
            ConstructionLoanAssumptions((D("100"), D("200")), D("0.70"), D("0.12"), D("0.01"))
        )

        self.assertEqual(result.months[0].loan_draw, D("70.00"))
        self.assertEqual(result.months[1].capitalized_interest, D("0.70"))
        self.assertEqual(result.ending_loan_balance, D("210.70"))
        self.assertEqual(result.origination_fee, D("2.10"))
        self.assertEqual(result.total_equity_contribution, D("92.10"))
