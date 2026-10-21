"""Maximum-price and configurable direct-return sensitivity analysis."""

from .advanced import (
    AdvancedSensitivityAssumptions,
    AdvancedSensitivityDimension,
    AdvancedSensitivityResult,
    AdvancedSensitivityScenario,
    SUPPORTED_DIMENSIONS,
    SUPPORTED_METRICS,
    calculate_advanced_sensitivity,
)
from .calculator import calculate_one_way_sensitivities
from .models import SensitivityAssumptions, SensitivityDimension, SensitivityPoint, SensitivityResult

__all__ = [
    "SensitivityAssumptions",
    "SensitivityDimension",
    "SensitivityPoint",
    "SensitivityResult",
    "calculate_one_way_sensitivities",
    "AdvancedSensitivityAssumptions",
    "AdvancedSensitivityDimension",
    "AdvancedSensitivityResult",
    "AdvancedSensitivityScenario",
    "SUPPORTED_DIMENSIONS",
    "SUPPORTED_METRICS",
    "calculate_advanced_sensitivity",
]
