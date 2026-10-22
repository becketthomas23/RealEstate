"""Deterministic Monte Carlo sampling over audited underwriting calculations."""

from decimal import Decimal
from random import Random
from statistics import NormalDist

from backend.core.validation import ZERO
from backend.workflows.underwriting import calculate_underwriting
from backend.workflows.underwriting.scenarios import apply_scenario_values, base_value

from .models import DriverImpact, MonteCarloAssumptions, MonteCarloResult, RepresentativeCase, SimulationSummary, SimulationVariable


AUTO_HALF_RANGES = {
    "rent_growth_rate": Decimal("0.02"),
    "exit_cap_rate": Decimal("0.01"),
    "vacancy_rate": Decimal("0.02"),
    "expense_growth_rate": Decimal("0.02"),
    "annual_interest_rate": Decimal("0.015"),
}
CONFIDENCE_LEVEL_MULTIPLIERS = {
    "low": Decimal("1.25"),
    "medium": Decimal("0.75"),
    "high": Decimal("0.35"),
}


def calculate_monte_carlo(assumptions: MonteCarloAssumptions) -> MonteCarloResult:
    """Run reproducible uniform samples and summarize material return outcomes.

    When a user has not supplied an explicit range, confidence controls the
    half-range: 0% confidence uses 125% of the standard range and 100% uses
    25%. Explicit ranges always take priority.
    """
    random = Random(assumptions.seed)
    normal = NormalDist()
    keys = tuple(variable.key for variable in assumptions.variables)
    cholesky = _cholesky(_correlation_matrix(keys, assumptions))
    irr_values: list[Decimal] = []
    multiple_values: list[Decimal] = []
    noi_values: list[Decimal] = []
    sale_values: list[Decimal] = []
    operating_cash_flow_values: list[Decimal] = []
    sampled_values: dict[str, list[Decimal]] = {key: [] for key in keys}
    cases: list[tuple[Decimal, dict[str, Decimal]]] = []
    for _ in range(assumptions.iterations):
        independent_normals = [random.gauss(0, 1) for _ in assumptions.variables]
        correlated_normals = [sum(cholesky[row][column] * independent_normals[column] for column in range(row + 1)) for row in range(len(keys))]
        values = {
            variable.key: _sample(
                variable,
                base_value(assumptions.underwriting, variable.key),
                unit_interval=Decimal(str(normal.cdf(correlated_normals[index]))),
            )
            for index, variable in enumerate(assumptions.variables)
        }
        result = calculate_underwriting(apply_scenario_values(assumptions.underwriting, values))
        for key, value in values.items():
            sampled_values[key].append(value)
        irr_values.append(result.returns.levered_irr)
        cases.append((result.returns.levered_irr, values))
        multiple_values.append(result.returns.equity_multiple)
        noi_values.append(result.terminal_noi)
        sale_values.append(result.disposition.net_sale_proceeds_to_equity)
        # This deliberately excludes sale proceeds. It reports the amount of
        # recurring property cash flow generated across the selected hold,
        # whereas IRR captures both operating and terminal-value effects.
        operating_cash_flow_values.append(sum(result.annual_operating_cash_flows, ZERO))
    return MonteCarloResult(
        iterations=assumptions.iterations,
        seed=assumptions.seed,
        variables=assumptions.variables,
        levered_irr=_summary("levered_irr", irr_values, assumptions.target_levered_irr),
        equity_multiple=_summary("equity_multiple", multiple_values),
        terminal_noi=_summary("terminal_noi", noi_values),
        net_sale_proceeds=_summary("net_sale_proceeds", sale_values),
        correlations=assumptions.correlations,
        driver_impacts=_driver_impacts(
            sampled_values,
            irr_values,
            operating_cash_flow_values,
            assumptions.underwriting,
        ),
        market_context=assumptions.market_context,
        downside_case=_representative_case("P10 downside case", cases, Decimal("0.10")),
        upside_case=_representative_case("P90 upside case", cases, Decimal("0.90")),
    )


def _sample(variable: SimulationVariable, base: Decimal, random: Random | None = None, unit_interval: Decimal | None = None) -> Decimal:
    if variable.minimum is not None:
        minimum, maximum = variable.minimum, variable.maximum
    else:
        # The qualitative confidence level establishes the primary band; the
        # numeric confidence then narrows it further. Low is deliberately the
        # widest case and high the narrowest at every numeric confidence level.
        confidence_factor = CONFIDENCE_LEVEL_MULTIPLIERS[variable.confidence_level] * (
            Decimal("1.25") - variable.confidence_percentage / Decimal("100")
        )
        half_range = AUTO_HALF_RANGES[variable.key] * confidence_factor
        minimum, maximum = base - half_range, base + half_range
        if variable.key in {"exit_cap_rate", "vacancy_rate", "annual_interest_rate"}:
            minimum = max(minimum, ZERO if variable.key != "exit_cap_rate" else Decimal("0.0001"))
        maximum = min(maximum, Decimal("0.9999"))
    if unit_interval is None:
        if random is None:
            raise ValueError("random generator or unit interval is required")
        unit_interval = Decimal(str(random.random()))
    return minimum + (maximum - minimum) * unit_interval


def _correlation_matrix(keys: tuple[str, ...], assumptions: MonteCarloAssumptions) -> list[list[float]]:
    matrix = [[1.0 if row == column else 0.0 for column in range(len(keys))] for row in range(len(keys))]
    positions = {key: index for index, key in enumerate(keys)}
    for correlation in assumptions.correlations:
        first, second = positions[correlation.first_key], positions[correlation.second_key]
        matrix[first][second] = float(correlation.coefficient)
        matrix[second][first] = float(correlation.coefficient)
    return matrix


def _cholesky(matrix: list[list[float]]) -> list[list[float]]:
    """Validate a positive-definite correlation matrix and return its factor."""
    size = len(matrix)
    result = [[0.0 for _ in range(size)] for _ in range(size)]
    for row in range(size):
        for column in range(row + 1):
            subtotal = sum(result[row][index] * result[column][index] for index in range(column))
            if row == column:
                diagonal = matrix[row][row] - subtotal
                if diagonal <= 1e-12:
                    raise ValueError("correlations must form a positive-definite matrix")
                result[row][column] = diagonal**0.5
            else:
                result[row][column] = (matrix[row][column] - subtotal) / result[column][column]
    return result


def _summary(metric: str, values: list[Decimal], target: Decimal | None = None) -> SimulationSummary:
    ordered = sorted(values)
    count = len(ordered)
    return SimulationSummary(
        metric=metric,
        minimum=ordered[0],
        percentile_10=_percentile(ordered, Decimal("0.10")),
        percentile_50=_percentile(ordered, Decimal("0.50")),
        percentile_90=_percentile(ordered, Decimal("0.90")),
        maximum=ordered[-1],
        mean=sum(ordered, ZERO) / count,
        probability_meeting_target=(sum(value >= target for value in ordered) / Decimal(count) if target is not None else None),
    )


def _driver_impacts(
    sampled_values: dict[str, list[Decimal]],
    irr_values: list[Decimal],
    operating_cash_flow_values: list[Decimal],
    underwriting,
) -> tuple[DriverImpact, ...]:
    irr_correlations = {key: _pearson(values, irr_values) for key, values in sampled_values.items()}
    cash_flow_correlations = {
        key: _pearson(values, operating_cash_flow_values) for key, values in sampled_values.items()
    }
    total = sum(abs(value) for value in irr_correlations.values())
    base_result = calculate_underwriting(underwriting)
    base_operating_cash_flow = sum(base_result.annual_operating_cash_flows, ZERO)
    direct_effects = {
        key: _direct_effect_per_100_bps(underwriting, key, base_result.returns.levered_irr, base_operating_cash_flow)
        for key in sampled_values
    }
    return tuple(
        DriverImpact(
            key=key,
            return_correlation=irr_correlation,
            cash_flow_correlation=cash_flow_correlations[key],
            relative_influence=abs(irr_correlation) / total if total else ZERO,
            cash_flow_change_per_100_bps=direct_effects[key][0],
            irr_change_per_100_bps=direct_effects[key][1],
        )
        for key, irr_correlation in sorted(irr_correlations.items(), key=lambda item: abs(item[1]), reverse=True)
    )


def _direct_effect_per_100_bps(underwriting, key: str, base_irr: Decimal, base_operating_cash_flow: Decimal) -> tuple[Decimal, Decimal]:
    """Calculate a direct rate effect while keeping every other input fixed."""
    current = base_value(underwriting, key)
    change = Decimal("0.01") if current + Decimal("0.01") < Decimal("0.9999") else Decimal("-0.01")
    scenario = calculate_underwriting(apply_scenario_values(underwriting, {key: current + change}))
    scale = Decimal("0.01") / change
    return (
        (sum(scenario.annual_operating_cash_flows, ZERO) - base_operating_cash_flow) * scale,
        (scenario.returns.levered_irr - base_irr) * scale,
    )


def _representative_case(label: str, cases: list[tuple[Decimal, dict[str, Decimal]]], percentile: Decimal) -> RepresentativeCase:
    """Return an observed joint case nearest the requested ordered percentile."""
    ordered = sorted(cases, key=lambda item: item[0])
    index = round((len(ordered) - 1) * float(percentile))
    levered_irr, values = ordered[index]
    return RepresentativeCase(label=label, levered_irr=levered_irr, values=values)


def _pearson(first: list[Decimal], second: list[Decimal]) -> Decimal:
    first_mean = sum(first, ZERO) / Decimal(len(first))
    second_mean = sum(second, ZERO) / Decimal(len(second))
    numerator = sum((left - first_mean) * (right - second_mean) for left, right in zip(first, second, strict=True))
    first_sum = sum((value - first_mean) ** 2 for value in first)
    second_sum = sum((value - second_mean) ** 2 for value in second)
    if first_sum == ZERO or second_sum == ZERO:
        return ZERO
    return numerator / Decimal(str((float(first_sum * second_sum)) ** 0.5))


def _percentile(values: list[Decimal], percentile: Decimal) -> Decimal:
    index = (len(values) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    fraction = index - lower
    return values[lower] + (values[upper] - values[lower]) * fraction
