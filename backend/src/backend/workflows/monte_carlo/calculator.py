"""Deterministic Monte Carlo sampling over audited underwriting calculations."""

from decimal import Decimal
from random import Random
from statistics import NormalDist, pstdev

from backend.core.validation import ZERO
from backend.workflows.underwriting import calculate_underwriting
from backend.workflows.underwriting.scenarios import apply_scenario_values, base_value

from .models import (
    DriverImpact,
    HistogramBin,
    MonteCarloAssumptions,
    MonteCarloResult,
    RepresentativeCase,
    SampledRange,
    SimulationSummary,
    SimulationVariable,
)


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
HISTOGRAM_BINS = 20
# A truncated normal treats the band as a 90% interval: ±1.645 standard deviations.
NORMAL_BAND_Z = 1.6448536269514722
_NORMAL = NormalDist()


def calculate_monte_carlo(assumptions: MonteCarloAssumptions) -> MonteCarloResult:
    """Run reproducible correlated samples and summarize material return outcomes.

    Draws start as correlated standard normals (Gaussian copula through a
    Cholesky factor), are mapped to the unit interval, then through each
    variable's marginal distribution so every driver keeps its own shape and
    band while still moving with the others.
    """
    random = Random(assumptions.seed)
    keys = tuple(variable.key for variable in assumptions.variables)
    cholesky = _cholesky(_correlation_matrix(keys, assumptions))
    ranges = {variable.key: sampled_range(variable, base_value(assumptions.underwriting, variable.key)) for variable in assumptions.variables}
    irr_values: list[Decimal] = []
    multiple_values: list[Decimal] = []
    noi_values: list[Decimal] = []
    sale_values: list[Decimal] = []
    dscr_values: list[Decimal] = []
    cash_on_cash_values: list[Decimal] = []
    operating_cash_flow_values: list[Decimal] = []
    negative_year_cases = 0
    sampled_values: dict[str, list[Decimal]] = {key: [] for key in keys}
    cases: list[tuple[Decimal, dict[str, Decimal]]] = []
    for _ in range(assumptions.iterations):
        independent_normals = [random.gauss(0, 1) for _ in assumptions.variables]
        correlated_normals = [
            sum(cholesky[row][column] * independent_normals[column] for column in range(row + 1)) for row in range(len(keys))
        ]
        values = {
            key: _draw(ranges[key], _NORMAL.cdf(correlated_normals[index]))
            for index, key in enumerate(keys)
        }
        result = calculate_underwriting(apply_scenario_values(assumptions.underwriting, values))
        for key, value in values.items():
            sampled_values[key].append(value)
        irr_values.append(result.returns.levered_irr)
        cases.append((result.returns.levered_irr, values))
        multiple_values.append(result.returns.equity_multiple)
        noi_values.append(result.terminal_noi)
        sale_values.append(result.disposition.net_sale_proceeds_to_equity)
        cash_on_cash_values.append(result.returns.cash_on_cash_by_year[0])
        if result.returns.minimum_dscr is not None:
            dscr_values.append(result.returns.minimum_dscr)
        if any(flow < ZERO for flow in result.annual_operating_cash_flows):
            negative_year_cases += 1
        # This deliberately excludes sale proceeds. It reports the amount of
        # recurring property cash flow generated across the selected hold,
        # whereas IRR captures both operating and terminal-value effects.
        operating_cash_flow_values.append(sum(result.annual_operating_cash_flows, ZERO))
    count = Decimal(assumptions.iterations)
    base_result = calculate_underwriting(assumptions.underwriting)
    return MonteCarloResult(
        iterations=assumptions.iterations,
        seed=assumptions.seed,
        variables=assumptions.variables,
        sampled_ranges=tuple(ranges[key] for key in keys),
        levered_irr=_summary("levered_irr", irr_values, assumptions.target_levered_irr),
        equity_multiple=_summary("equity_multiple", multiple_values),
        terminal_noi=_summary("terminal_noi", noi_values),
        net_sale_proceeds=_summary("net_sale_proceeds", sale_values),
        minimum_dscr=_summary("minimum_dscr", dscr_values, assumptions.minimum_dscr) if dscr_values else None,
        year_one_cash_on_cash=_summary("year_one_cash_on_cash", cash_on_cash_values),
        irr_histogram=_histogram(irr_values),
        probability_of_loss=Decimal(sum(value < ZERO for value in irr_values)) / count,
        probability_dscr_below_floor=(
            Decimal(sum(value < assumptions.minimum_dscr for value in dscr_values)) / count
            if dscr_values and assumptions.minimum_dscr is not None
            else None
        ),
        probability_negative_cash_flow_year=Decimal(negative_year_cases) / count,
        correlations=assumptions.correlations,
        driver_impacts=_driver_impacts(sampled_values, irr_values, operating_cash_flow_values, assumptions.underwriting, base_result, ranges),
        market_context=assumptions.market_context,
        downside_case=_representative_case("P10 downside case", cases, Decimal("0.10")),
        upside_case=_representative_case("P90 upside case", cases, Decimal("0.90")),
        base_case_irr=base_result.returns.levered_irr,
    )


def sampled_range(variable: SimulationVariable, base: Decimal) -> SampledRange:
    """Resolve the band a variable is drawn from, with the mode inside it."""
    if variable.minimum is not None and variable.maximum is not None:
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
    mode = variable.mode if variable.mode is not None else min(max(base, minimum), maximum)
    return SampledRange(variable.key, variable.distribution, minimum, mode, maximum)


def _draw(band: SampledRange, unit_interval: float) -> Decimal:
    """Map a uniform draw through the band's marginal distribution."""
    u = min(max(unit_interval, 1e-9), 1 - 1e-9)
    low, mode, high = float(band.minimum), float(band.mode), float(band.maximum)
    width = high - low
    if width <= 0:
        return band.minimum
    if band.distribution == "uniform":
        value = low + width * u
    elif band.distribution == "triangular":
        split = (mode - low) / width
        if u < split:
            value = low + (u * width * (mode - low)) ** 0.5
        else:
            value = high - ((1 - u) * width * (high - mode)) ** 0.5
    else:
        sigma = width / (2 * NORMAL_BAND_Z)
        lower_cdf = _NORMAL.cdf((low - mode) / sigma)
        upper_cdf = _NORMAL.cdf((high - mode) / sigma)
        value = mode + sigma * _NORMAL.inv_cdf(lower_cdf + u * (upper_cdf - lower_cdf))
    value = min(max(value, low), high)
    return Decimal(str(round(value, 10)))


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
        percentile_5=_percentile(ordered, Decimal("0.05")),
        percentile_10=_percentile(ordered, Decimal("0.10")),
        percentile_25=_percentile(ordered, Decimal("0.25")),
        percentile_50=_percentile(ordered, Decimal("0.50")),
        percentile_75=_percentile(ordered, Decimal("0.75")),
        percentile_90=_percentile(ordered, Decimal("0.90")),
        percentile_95=_percentile(ordered, Decimal("0.95")),
        maximum=ordered[-1],
        mean=sum(ordered, ZERO) / count,
        standard_deviation=Decimal(str(pstdev(float(value) for value in ordered))) if count > 1 else ZERO,
        probability_meeting_target=(sum(value >= target for value in ordered) / Decimal(count) if target is not None else None),
    )


def _histogram(values: list[Decimal]) -> tuple[HistogramBin, ...]:
    """Equal-width bins across the observed range, for a distribution chart."""
    low, high = float(min(values)), float(max(values))
    if high <= low:
        return (HistogramBin(Decimal(str(low)), Decimal(str(high)), len(values)),)
    bins = min(HISTOGRAM_BINS, max(5, len(values) // 25))
    width = (high - low) / bins
    counts = [0] * bins
    for value in values:
        index = min(int((float(value) - low) / width), bins - 1)
        counts[index] += 1
    exact_low, exact_high = min(values), max(values)
    return tuple(
        HistogramBin(
            exact_low if index == 0 else Decimal(str(round(low + index * width, 8))),
            exact_high if index == bins - 1 else Decimal(str(round(low + (index + 1) * width, 8))),
            count,
        )
        for index, count in enumerate(counts)
    )


def _driver_impacts(
    sampled_values: dict[str, list[Decimal]],
    irr_values: list[Decimal],
    operating_cash_flow_values: list[Decimal],
    underwriting,
    base_result,
    ranges: dict[str, SampledRange],
) -> tuple[DriverImpact, ...]:
    irr_correlations = {key: _pearson(values, irr_values) for key, values in sampled_values.items()}
    cash_flow_correlations = {key: _pearson(values, operating_cash_flow_values) for key, values in sampled_values.items()}
    total = sum(abs(value) for value in irr_correlations.values())
    base_operating_cash_flow = sum(base_result.annual_operating_cash_flows, ZERO)
    impacts = []
    for key, irr_correlation in sorted(irr_correlations.items(), key=lambda item: abs(item[1]), reverse=True):
        cash_flow_effect, irr_effect = _direct_effect_per_100_bps(underwriting, key, base_result.returns.levered_irr, base_operating_cash_flow)
        ordered = sorted(sampled_values[key])
        low, high = _percentile(ordered, Decimal("0.10")), _percentile(ordered, Decimal("0.90"))
        impacts.append(
            DriverImpact(
                key=key,
                return_correlation=irr_correlation,
                cash_flow_correlation=cash_flow_correlations[key],
                relative_influence=abs(irr_correlation) / total if total else ZERO,
                cash_flow_change_per_100_bps=cash_flow_effect,
                irr_change_per_100_bps=irr_effect,
                irr_at_low=_irr_at(underwriting, key, low),
                irr_at_high=_irr_at(underwriting, key, high),
                sampled_low=low,
                sampled_high=high,
            )
        )
    return tuple(impacts)


def _irr_at(underwriting, key: str, value: Decimal) -> Decimal | None:
    try:
        return calculate_underwriting(apply_scenario_values(underwriting, {key: value})).returns.levered_irr
    except ValueError:
        return None


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
