"""Input and output contracts for the disposition engine."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import ZERO, require_non_negative, require_rate


@dataclass(frozen=True, slots=True)
class DispositionAssumptions:
    terminal_noi: Decimal
    exit_cap_rate: Decimal
    selling_cost_rate: Decimal
    loan_payoff: Decimal = ZERO

    def __post_init__(self) -> None:
        require_non_negative("terminal_noi", self.terminal_noi)
        if not ZERO < self.exit_cap_rate < Decimal("1"):
            raise ValueError("exit_cap_rate must be between 0 and 1")
        require_rate("selling_cost_rate", self.selling_cost_rate)
        require_non_negative("loan_payoff", self.loan_payoff)


@dataclass(frozen=True, slots=True)
class DispositionResult:
    gross_sale_price: Decimal
    selling_costs: Decimal
    net_sale_proceeds_before_debt: Decimal
    loan_payoff: Decimal
    net_sale_proceeds_to_equity: Decimal
