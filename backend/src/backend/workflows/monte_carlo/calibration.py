"""Parse an auditable, aggregate historical market calibration CSV."""

import csv
from dataclasses import dataclass
from decimal import Decimal
from io import StringIO
from math import sqrt

from .models import Correlation, HistoricalRange, MarketContext, SUPPORTED_VARIABLES


CALIBRATION_FIELDS = (
    "period",
    "property_type",
    "value_bucket",
    "rent_growth_rate",
    "exit_cap_rate",
    "vacancy_rate",
    "expense_growth_rate",
    "annual_interest_rate",
)


@dataclass(frozen=True, slots=True)
class MarketCalibration:
    context: MarketContext
    correlations: tuple[Correlation, ...]
    driver_ranges: tuple[HistoricalRange, ...]
    warnings: tuple[str, ...]


def market_calibration_csv_template() -> str:
    """Return the aggregate quarterly CSV format used for a calibration preview."""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CALIBRATION_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "period": "2022-Q1",
            "property_type": "Multifamily",
            "value_bucket": "$10M-$25M",
            "rent_growth_rate": "0.035",
            "exit_cap_rate": "0.0475",
            "vacancy_rate": "0.045",
            "expense_growth_rate": "0.028",
            "annual_interest_rate": "0.042",
        }
    )
    return output.getvalue()


def calculate_market_calibration(contents: bytes, property_type: str, value_bucket: str, source: str) -> MarketCalibration:
    """Calculate Pearson correlations for a single aggregate market segment.

    The CSV deliberately contains only periodic aggregate metrics.  It does not
    require or retain individual property, owner, tenant, or transaction data.
    """
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("CSV must be UTF-8 encoded") from error
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV must include a header row")
    headers = tuple(header.strip() for header in reader.fieldnames)
    if set(headers) != set(CALIBRATION_FIELDS) or len(headers) != len(CALIBRATION_FIELDS):
        raise ValueError("CSV headers must exactly match the market-calibration template")
    rows = [
        {key: (value or "").strip() for key, value in row.items()}
        for row in reader
        if any((value or "").strip() for value in row.values())
    ]
    selected = [row for row in rows if row["property_type"] == property_type and row["value_bucket"] == value_bucket]
    if len(selected) < 8:
        raise ValueError("at least 8 complete periods are required for the selected property type and value bucket")
    values: dict[str, list[Decimal]] = {key: [] for key in SUPPORTED_VARIABLES}
    periods: list[str] = []
    for row in selected:
        try:
            metrics = {key: _parse_rate(row[key]) for key in SUPPORTED_VARIABLES}
        except Exception as error:
            raise ValueError("market-calibration rates must be decimal values (0.05 means 5%)") from error
        values = {key: values[key] + [metrics[key]] for key in SUPPORTED_VARIABLES}
        periods.append(row["period"])
    correlations = tuple(
        Correlation(first, second, _pearson(values[first], values[second]))
        for index, first in enumerate(sorted(SUPPORTED_VARIABLES))
        for second in sorted(SUPPORTED_VARIABLES)[index + 1 :]
    )
    driver_ranges = tuple(
        HistoricalRange(
            key=key,
            percentile_10=_percentile(values[key], Decimal("0.10")),
            percentile_50=_percentile(values[key], Decimal("0.50")),
            percentile_90=_percentile(values[key], Decimal("0.90")),
        )
        for key in sorted(SUPPORTED_VARIABLES)
    )
    return MarketCalibration(
        context=MarketContext(
            property_type=property_type,
            value_bucket=value_bucket,
            source=source.strip() or "Historical market CSV",
            observations=len(selected),
            period_start=min(periods),
            period_end=max(periods),
        ),
        correlations=correlations,
        driver_ranges=driver_ranges,
        warnings=_quality_warnings(len(selected)),
    )


def _pearson(first: list[Decimal], second: list[Decimal]) -> Decimal:
    first_mean = sum(first) / Decimal(len(first))
    second_mean = sum(second) / Decimal(len(second))
    numerator = sum((left - first_mean) * (right - second_mean) for left, right in zip(first, second, strict=True))
    left_sum = sum((value - first_mean) ** 2 for value in first)
    right_sum = sum((value - second_mean) ** 2 for value in second)
    if left_sum == 0 or right_sum == 0:
        raise ValueError("each market metric must change across the selected periods")
    return max(Decimal("-0.999"), min(Decimal("0.999"), numerator / Decimal(str(sqrt(float(left_sum * right_sum))))))


def _percentile(values: list[Decimal], percentile: Decimal) -> Decimal:
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _parse_rate(value: str) -> Decimal:
    """Accept template decimals and conventional percent-formatted exports."""
    normalized = value.strip().replace(",", "")
    if normalized.endswith("%"):
        return Decimal(normalized[:-1].strip()) / Decimal("100")
    return Decimal(normalized)


def _quality_warnings(observations: int) -> tuple[str, ...]:
    if observations < 20:
        return (f"Limited history: {observations} periods. Use 20 or more comparable periods when available.",)
    return ()
