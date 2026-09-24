"""Pure, deterministic financial-calculation engines.

Engines do not read databases or HTTP requests.  That keeps each assumption set
reproducible and makes the same calculation safe to rerun in sensitivities.
"""

from .debt import DebtAssumptions, DebtYear, project_debt
from .disposition import DispositionAssumptions, DispositionResult, calculate_disposition
from .operating import OperatingAssumptions, OperatingYear, project_operations
from .returns import ReturnAssumptions, ReturnMetrics, calculate_returns

__all__ = ["DebtAssumptions", "DebtYear", "DispositionAssumptions", "DispositionResult", "OperatingAssumptions", "OperatingYear", "ReturnAssumptions", "ReturnMetrics", "calculate_disposition", "calculate_returns", "project_debt", "project_operations"]
