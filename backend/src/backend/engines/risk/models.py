"""Risk-flag result contract shared by underwriting presentations and exports."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RiskFlag:
    code: str
    severity: str
    message: str
    observed_value: Decimal
    threshold: Decimal
