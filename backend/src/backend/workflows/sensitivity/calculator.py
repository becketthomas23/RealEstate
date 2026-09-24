"""Rerun the price solver one assumption at a time."""

from dataclasses import replace
from decimal import Decimal

from backend.core.validation import ZERO
from backend.solvers.pricing import MaximumPriceAssumptions, solve_maximum_purchase_price

from .models import SensitivityAssumptions, SensitivityDimension, SensitivityPoint, SensitivityResult


RENT_GROWTH_STEP = Decimal("0.01")
EXIT_CAP_RATE_STEP = Decimal("0.005")
INTEREST_RATE_STEP = Decimal("0.01")


def calculate_one_way_sensitivities(assumptions: SensitivityAssumptions) -> SensitivityResult:
    """Return lower/base/higher cases while holding every other input constant.

    Rent growth and interest-rate steps are 100 basis points; exit-cap steps are
    50 basis points. Each point uses the caller's explicit solver bracket.
    An unavailable scenario is returned with its reason instead of hiding the
    rest of the analysis.
    """
    underwriting = assumptions.underwriting
    return SensitivityResult(
        dimensions=(
            _dimension(
                "rent_growth_rate",
                "Rent growth",
                "rate",
                _three_points(underwriting.operating.rent_growth_rate, RENT_GROWTH_STEP, lower_bound=None),
                lambda value: replace(underwriting, operating=replace(underwriting.operating, rent_growth_rate=value)),
                assumptions,
            ),
            _dimension(
                "exit_cap_rate",
                "Exit cap rate",
                "rate",
                _three_points(underwriting.exit_cap_rate, EXIT_CAP_RATE_STEP, lower_bound=ZERO),
                lambda value: replace(underwriting, exit_cap_rate=value),
                assumptions,
            ),
            _dimension(
                "annual_interest_rate",
                "Interest rate",
                "rate",
                _three_points(underwriting.annual_interest_rate, INTEREST_RATE_STEP, lower_bound=ZERO),
                lambda value: replace(underwriting, annual_interest_rate=value),
                assumptions,
            ),
        )
    )


def _three_points(base: Decimal, step: Decimal, *, lower_bound: Decimal | None) -> tuple[tuple[str, Decimal], ...]:
    lower = base - step
    if lower_bound is not None:
        lower = max(lower, lower_bound)
    candidates = (("Lower", lower), ("Base", base), ("Higher", base + step))
    unique: list[tuple[str, Decimal]] = []
    for label, value in candidates:
        if not any(value == existing for _, existing in unique):
            unique.append((label, value))
    return tuple(unique)


def _dimension(key, label, unit, points, mutate, assumptions: SensitivityAssumptions) -> SensitivityDimension:
    return SensitivityDimension(
        key=key,
        label=label,
        unit=unit,
        points=tuple(_solve_point(point_label, value, mutate(value), assumptions) for point_label, value in points),
    )


def _solve_point(label: str, value: Decimal, underwriting, assumptions: SensitivityAssumptions) -> SensitivityPoint:
    try:
        result = solve_maximum_purchase_price(
            MaximumPriceAssumptions(
                underwriting=underwriting,
                target_levered_irr=assumptions.target_levered_irr,
                minimum_dscr=assumptions.minimum_dscr,
                minimum_purchase_price=assumptions.minimum_purchase_price,
                maximum_purchase_price=assumptions.maximum_purchase_price,
                price_tolerance=assumptions.price_tolerance,
                max_iterations=assumptions.max_iterations,
            )
        )
    except ValueError as error:
        return SensitivityPoint(label, value, None, str(error))
    return SensitivityPoint(label, value, result.maximum_purchase_price, None)
