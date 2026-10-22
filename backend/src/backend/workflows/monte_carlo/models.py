"""Typed contracts for reproducible Monte Carlo underwriting runs."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import ZERO, require_rate, require_return_rate
from backend.workflows.underwriting import UnderwritingAssumptions


SUPPORTED_VARIABLES = {
    "rent_growth_rate",
    "exit_cap_rate",
    "vacancy_rate",
    "expense_growth_rate",
    "annual_interest_rate",
}
CONFIDENCE_LEVELS = {"low", "medium", "high"}


@dataclass(frozen=True, slots=True)
class Correlation:
    """One off-diagonal entry in a driver correlation matrix."""

    first_key: str
    second_key: str
    coefficient: Decimal

    def __post_init__(self) -> None:
        if self.first_key not in SUPPORTED_VARIABLES or self.second_key not in SUPPORTED_VARIABLES:
            raise ValueError("correlation keys must be supported simulation variables")
        if self.first_key == self.second_key:
            raise ValueError("a correlation must use two different variables")
        if not Decimal("-0.999") <= self.coefficient <= Decimal("0.999"):
            raise ValueError("correlation coefficient must be between -0.999 and 0.999")

    @property
    def normalized_keys(self) -> tuple[str, str]:
        return tuple(sorted((self.first_key, self.second_key)))


@dataclass(frozen=True, slots=True)
class MarketContext:
    """Provenance for a market calibration attached to an auditable run."""

    property_type: str
    value_bucket: str
    source: str
    source_as_of_date: str
    observations: int
    period_start: str
    period_end: str


@dataclass(frozen=True, slots=True)
class HistoricalRange:
    """Historical distribution for one market driver within a segment."""

    key: str
    percentile_10: Decimal
    percentile_50: Decimal
    percentile_90: Decimal


@dataclass(frozen=True, slots=True)
class DriverImpact:
    """Observed driver associations and effects in a simulated deal run.

    The two per-100-basis-point values are controlled, one-driver-at-a-time
    effects from the base case. The correlation values remain associations
    across joint simulated cases, so correlated drivers can still share the
    same underlying market movement.
    """

    key: str
    return_correlation: Decimal
    cash_flow_correlation: Decimal
    relative_influence: Decimal
    cash_flow_change_per_100_bps: Decimal
    irr_change_per_100_bps: Decimal


@dataclass(frozen=True, slots=True)
class RepresentativeCase:
    """A generated joint driver case nearest a reported return percentile."""

    label: str
    levered_irr: Decimal
    values: dict[str, Decimal]


@dataclass(frozen=True, slots=True)
class SimulationVariable:
    key: str
    confidence_level: str
    confidence_percentage: Decimal
    minimum: Decimal | None = None
    maximum: Decimal | None = None

    def __post_init__(self) -> None:
        if self.key not in SUPPORTED_VARIABLES:
            raise ValueError(f"unsupported simulation variable: {self.key}")
        if self.confidence_level not in CONFIDENCE_LEVELS:
            raise ValueError("confidence_level must be low, medium, or high")
        if not ZERO <= self.confidence_percentage <= Decimal("100"):
            raise ValueError("confidence_percentage must be between 0 and 100")
        if (self.minimum is None) != (self.maximum is None):
            raise ValueError("minimum and maximum must be supplied together")
        if self.minimum is not None:
            require_rate(self.key, self.minimum, allow_negative=self.key in {"rent_growth_rate", "expense_growth_rate"})
            require_rate(self.key, self.maximum, allow_negative=self.key in {"rent_growth_rate", "expense_growth_rate"})
            if self.minimum >= self.maximum:
                raise ValueError("simulation minimum must be less than maximum")
            if self.key == "exit_cap_rate" and self.minimum <= ZERO:
                raise ValueError("exit cap rate minimum must be greater than zero")


@dataclass(frozen=True, slots=True)
class MonteCarloAssumptions:
    underwriting: UnderwritingAssumptions
    variables: tuple[SimulationVariable, ...]
    iterations: int = 1_000
    seed: int = 0
    target_levered_irr: Decimal | None = None
    correlations: tuple[Correlation, ...] = ()
    market_context: MarketContext | None = None

    def __post_init__(self) -> None:
        if not 1 <= len(self.variables) <= 5:
            raise ValueError("select between 1 and 5 simulation variables")
        keys = tuple(variable.key for variable in self.variables)
        if len(set(keys)) != len(keys):
            raise ValueError("simulation variables must be unique")
        selected = set(keys)
        correlation_pairs = set()
        for correlation in self.correlations:
            if correlation.first_key not in selected or correlation.second_key not in selected:
                raise ValueError("correlation keys must be selected simulation variables")
            if correlation.normalized_keys in correlation_pairs:
                raise ValueError("each driver pair can have only one correlation")
            correlation_pairs.add(correlation.normalized_keys)
        if not 100 <= self.iterations <= 10_000:
            raise ValueError("iterations must be between 100 and 10000")
        if self.target_levered_irr is not None:
            require_return_rate("target_levered_irr", self.target_levered_irr)


@dataclass(frozen=True, slots=True)
class SimulationSummary:
    metric: str
    minimum: Decimal
    percentile_10: Decimal
    percentile_50: Decimal
    percentile_90: Decimal
    maximum: Decimal
    mean: Decimal
    probability_meeting_target: Decimal | None


@dataclass(frozen=True, slots=True)
class MonteCarloResult:
    iterations: int
    seed: int
    variables: tuple[SimulationVariable, ...]
    levered_irr: SimulationSummary
    equity_multiple: SimulationSummary
    terminal_noi: SimulationSummary
    net_sale_proceeds: SimulationSummary
    correlations: tuple[Correlation, ...]
    driver_impacts: tuple[DriverImpact, ...]
    market_context: MarketContext | None
    downside_case: RepresentativeCase
    upside_case: RepresentativeCase
