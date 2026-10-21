"""Single-LP / single-sponsor equity-waterfall engine."""

from .calculator import calculate_waterfall
from .models import WaterfallAssumptions, WaterfallResult, WaterfallYear

__all__ = ["WaterfallAssumptions", "WaterfallResult", "WaterfallYear", "calculate_waterfall"]
