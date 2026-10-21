"""Configurable direct-return sensitivity analysis.

This workflow is intentionally separate from the reverse-price sensitivity
workflow.  It reruns the audited underwriting calculation for every selected
scenario rather than solving for a purchase price.
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from itertools import product

from backend.core.validation import ZERO, require_rate
from backend.workflows.underwriting import UnderwritingAssumptions, calculate_underwriting


SUPPORTED_DIMENSIONS = {
    "rent_growth_rate": "Rent growth",
    "exit_cap_rate": "Exit cap rate",
    "vacancy_rate": "Vacancy",
    "expense_growth_rate": "Expense growth",
    "annual_interest_rate": "Interest rate",
}
SUPPORTED_METRICS = {
    "levered_irr": "Levered IRR",
    "equity_multiple": "Equity multiple",
    "minimum_dscr": "Minimum DSCR",
    "terminal_noi": "Terminal NOI",
    "net_sale_proceeds": "Net sale proceeds to equity",
}


@dataclass(frozen=True, slots=True)
class AdvancedSensitivityDimension:
    key: str
    values: tuple[Decimal, ...]

    def __post_init__(self) -> None:
        if self.key not in SUPPORTED_DIMENSIONS:
            raise ValueError(f"unsupported sensitivity dimension: {self.key}")
        if not 2 <= len(self.values) <= 7:
            raise ValueError("each sensitivity dimension must contain between 2 and 7 values")
        if len(set(self.values)) != len(self.values):
            raise ValueError("sensitivity dimension values must be unique")
        for value in self.values:
            require_rate(self.key, value, allow_negative=self.key in {"rent_growth_rate", "expense_growth_rate"})
            if self.key == "exit_cap_rate" and value <= ZERO:
                raise ValueError("exit_cap_rate sensitivity values must be greater than zero")


@dataclass(frozen=True, slots=True)
class AdvancedSensitivityAssumptions:
    underwriting: UnderwritingAssumptions
    dimensions: tuple[AdvancedSensitivityDimension, ...]
    metric: str = "levered_irr"

    def __post_init__(self) -> None:
        if not 1 <= len(self.dimensions) <= 3:
            raise ValueError("select between 1 and 3 sensitivity dimensions")
        keys = tuple(dimension.key for dimension in self.dimensions)
        if len(set(keys)) != len(keys):
            raise ValueError("sensitivity dimensions must be unique")
        if self.metric not in SUPPORTED_METRICS:
            raise ValueError(f"unsupported sensitivity metric: {self.metric}")


@dataclass(frozen=True, slots=True)
class AdvancedSensitivityScenario:
    values: dict[str, Decimal]
    metric_value: Decimal | None
    error: str | None


@dataclass(frozen=True, slots=True)
class AdvancedSensitivityResult:
    metric: str
    dimensions: tuple[AdvancedSensitivityDimension, ...]
    scenarios: tuple[AdvancedSensitivityScenario, ...]


def calculate_advanced_sensitivity(assumptions: AdvancedSensitivityAssumptions) -> AdvancedSensitivityResult:
    """Calculate every selected scenario, retaining failures for auditability."""
    scenarios: list[AdvancedSensitivityScenario] = []
    for selected in product(*(dimension.values for dimension in assumptions.dimensions)):
        values = dict(zip((dimension.key for dimension in assumptions.dimensions), selected, strict=True))
        try:
            result = calculate_underwriting(_apply_values(assumptions.underwriting, values))
            metric_value = _metric_value(result, assumptions.metric)
        except ValueError as error:
            scenarios.append(AdvancedSensitivityScenario(values, None, str(error)))
        else:
            scenarios.append(AdvancedSensitivityScenario(values, metric_value, None))
    return AdvancedSensitivityResult(assumptions.metric, assumptions.dimensions, tuple(scenarios))


def _apply_values(underwriting: UnderwritingAssumptions, values: dict[str, Decimal]) -> UnderwritingAssumptions:
    operating = underwriting.operating
    if "rent_growth_rate" in values:
        # A sensitivity point represents a complete rent-growth case.  It
        # therefore intentionally replaces a detailed period schedule.
        operating = replace(operating, rent_growth_rate=values["rent_growth_rate"], annual_rent_growth_rates=None)
    if "vacancy_rate" in values:
        operating = replace(operating, vacancy_rate=values["vacancy_rate"])
    if "expense_growth_rate" in values:
        operating = replace(operating, expense_growth_rate=values["expense_growth_rate"])
    result = replace(underwriting, operating=operating)
    if "exit_cap_rate" in values:
        result = replace(result, exit_cap_rate=values["exit_cap_rate"])
    if "annual_interest_rate" in values:
        result = replace(result, annual_interest_rate=values["annual_interest_rate"])
    return result


def _metric_value(result, metric: str) -> Decimal:
    if metric == "levered_irr":
        return result.returns.levered_irr
    if metric == "equity_multiple":
        return result.returns.equity_multiple
    if metric == "minimum_dscr":
        if result.returns.minimum_dscr is None:
            raise ValueError("minimum DSCR is unavailable without debt service")
        return result.returns.minimum_dscr
    if metric == "terminal_noi":
        return result.terminal_noi
    return result.disposition.net_sale_proceeds_to_equity
