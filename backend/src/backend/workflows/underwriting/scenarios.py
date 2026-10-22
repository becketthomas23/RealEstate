"""Apply scenario values to an underwriting case without losing its structure."""

from dataclasses import replace
from decimal import Decimal

from backend.core.validation import ONE

from .models import UnderwritingAssumptions


SCENARIO_KEYS = ("rent_growth_rate", "exit_cap_rate", "vacancy_rate", "expense_growth_rate", "annual_interest_rate")
MINIMUM_RATE = Decimal("-1")
MAXIMUM_RATE = Decimal("0.9999")


def base_value(underwriting: UnderwritingAssumptions, key: str) -> Decimal:
    """Return the deal's current value for a scenario-able input."""
    if key == "rent_growth_rate":
        return underwriting.operating.rent_growth_rate
    if key == "vacancy_rate":
        return underwriting.operating.vacancy_rate
    if key == "expense_growth_rate":
        return underwriting.operating.expense_growth_rate
    return getattr(underwriting, key)


def apply_scenario_values(underwriting: UnderwritingAssumptions, values: dict[str, Decimal]) -> UnderwritingAssumptions:
    """Return a copy of the case with the supplied inputs replaced.

    A rent-growth scenario is interpreted relative to the base rent-growth
    rate. When the analyst entered a year-by-year schedule, every scheduled
    rate is shifted by the same amount instead of being replaced by a single
    flat rate, so the scenario still tests the deal that was modeled.
    """
    operating = underwriting.operating
    if "rent_growth_rate" in values:
        new_rate = values["rent_growth_rate"]
        if operating.annual_rent_growth_rates:
            shift = new_rate - operating.rent_growth_rate
            schedule = tuple(_clamp_rate(rate + shift) for rate in operating.annual_rent_growth_rates)
            operating = replace(operating, rent_growth_rate=new_rate, annual_rent_growth_rates=schedule)
        else:
            operating = replace(operating, rent_growth_rate=new_rate)
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


def _clamp_rate(rate: Decimal) -> Decimal:
    return min(max(rate, MINIMUM_RATE), MAXIMUM_RATE)
