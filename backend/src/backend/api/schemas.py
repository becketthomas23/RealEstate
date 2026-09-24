"""Request models for calculation and persisted-underwriting APIs."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiModel(BaseModel):
    """Reject unknown keys so assumption payloads remain auditable."""

    model_config = ConfigDict(extra="forbid")


class LoginRequest(ApiModel):
    password: str = Field(min_length=1, max_length=512)


class OperatingAssumptionsRequest(ApiModel):
    current_potential_gross_income: Decimal
    current_operating_expenses: Decimal
    vacancy_rate: Decimal
    rent_growth_rate: Decimal
    expense_growth_rate: Decimal
    hold_period_years: int = Field(ge=5, le=10)


class UnderwritingRequest(ApiModel):
    purchase_price: Decimal
    closing_cost_rate: Decimal
    loan_to_value: Decimal
    annual_interest_rate: Decimal
    amortization_years: int = Field(ge=1)
    exit_cap_rate: Decimal
    selling_cost_rate: Decimal
    operating: OperatingAssumptionsRequest


class MaximumPriceRequest(ApiModel):
    underwriting: UnderwritingRequest
    target_levered_irr: Decimal
    minimum_dscr: Decimal
    minimum_purchase_price: Decimal
    maximum_purchase_price: Decimal
    price_tolerance: Decimal = Decimal("0.01")
    max_iterations: int = Field(default=100, ge=1)


class DealCreateRequest(ApiModel):
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class AssumptionSetCreateRequest(ApiModel):
    """A named, immutable set of inputs with the context needed to audit it."""

    label: str = Field(default="Base case", min_length=1, max_length=200)
    source: str | None = Field(default=None, max_length=2000)
    effective_date: date = Field(default_factory=date.today)
    confidence_level: Literal["low", "medium", "high"] = "medium"
    underwriting: UnderwritingRequest

    @field_validator("label")
    @classmethod
    def strip_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("label must not be blank")
        return value


class SavedMaximumPriceRequest(ApiModel):
    target_levered_irr: Decimal
    minimum_dscr: Decimal
    minimum_purchase_price: Decimal
    maximum_purchase_price: Decimal
    price_tolerance: Decimal = Decimal("0.01")
    max_iterations: int = Field(default=100, ge=1)


class SensitivityRequest(MaximumPriceRequest):
    """A complete input set for a stateless one-way sensitivity analysis."""


class SavedSensitivityRequest(SavedMaximumPriceRequest):
    """Solver constraints for an already-persisted assumption set."""
