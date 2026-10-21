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
    annual_rent_growth_rates: list[Decimal] | None = Field(default=None, max_length=10)


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
    property_type: str = Field(default="Multifamily", min_length=1, max_length=100)
    value_bucket: str = Field(default="Custom", min_length=1, max_length=100)
    underwriting: UnderwritingRequest

    @field_validator("label")
    @classmethod
    def strip_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("label must not be blank")
        return value

    @field_validator("property_type", "value_bucket")
    @classmethod
    def strip_market_segment(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("market segment values must not be blank")
        return value


class SavedMaximumPriceRequest(ApiModel):
    target_levered_irr: Decimal
    minimum_dscr: Decimal
    minimum_purchase_price: Decimal
    maximum_purchase_price: Decimal
    price_tolerance: Decimal = Decimal("0.01")
    max_iterations: int = Field(default=100, ge=1)


class ScenarioComparisonRequest(SavedMaximumPriceRequest):
    """The common pricing constraints applied to every immutable deal version."""


class SensitivityRequest(MaximumPriceRequest):
    """A complete input set for a stateless one-way sensitivity analysis."""


class AdvancedSensitivityDimensionRequest(ApiModel):
    key: Literal["rent_growth_rate", "exit_cap_rate", "vacancy_rate", "expense_growth_rate", "annual_interest_rate"]
    values: list[Decimal] = Field(min_length=2, max_length=7)


class AdvancedSensitivityRequest(ApiModel):
    underwriting: UnderwritingRequest
    dimensions: list[AdvancedSensitivityDimensionRequest] = Field(min_length=1, max_length=3)
    metric: Literal["levered_irr", "equity_multiple", "minimum_dscr", "terminal_noi", "net_sale_proceeds"] = "levered_irr"


class SimulationVariableRequest(ApiModel):
    key: Literal["rent_growth_rate", "exit_cap_rate", "vacancy_rate", "expense_growth_rate", "annual_interest_rate"]
    confidence_level: Literal["low", "medium", "high"]
    confidence_percentage: Decimal = Field(ge=0, le=100)
    minimum: Decimal | None = None
    maximum: Decimal | None = None


class CorrelationRequest(ApiModel):
    first_key: Literal["rent_growth_rate", "exit_cap_rate", "vacancy_rate", "expense_growth_rate", "annual_interest_rate"]
    second_key: Literal["rent_growth_rate", "exit_cap_rate", "vacancy_rate", "expense_growth_rate", "annual_interest_rate"]
    coefficient: Decimal = Field(ge=Decimal("-0.999"), le=Decimal("0.999"))


class MarketContextRequest(ApiModel):
    property_type: str = Field(min_length=1, max_length=100)
    value_bucket: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=500)
    observations: int = Field(ge=8)
    period_start: str = Field(min_length=1, max_length=50)
    period_end: str = Field(min_length=1, max_length=50)


class MonteCarloRequest(ApiModel):
    underwriting: UnderwritingRequest
    variables: list[SimulationVariableRequest] = Field(min_length=1, max_length=5)
    iterations: int = Field(default=1_000, ge=100, le=10_000)
    seed: int = 0
    target_levered_irr: Decimal | None = None
    correlations: list[CorrelationRequest] = Field(default_factory=list, max_length=10)
    market_context: MarketContextRequest | None = None


class SavedMonteCarloRequest(ApiModel):
    variables: list[SimulationVariableRequest] = Field(min_length=1, max_length=5)
    iterations: int = Field(default=1_000, ge=100, le=10_000)
    seed: int = 0
    target_levered_irr: Decimal | None = None
    correlations: list[CorrelationRequest] = Field(default_factory=list, max_length=10)
    market_context: MarketContextRequest | None = None


class WaterfallRequest(ApiModel):
    underwriting: UnderwritingRequest
    preferred_return_rate: Decimal
    sponsor_residual_share: Decimal


class SavedWaterfallRequest(ApiModel):
    preferred_return_rate: Decimal
    sponsor_residual_share: Decimal


class ConstructionLoanRequest(ApiModel):
    monthly_project_costs: list[Decimal] = Field(min_length=1, max_length=120)
    loan_to_cost: Decimal
    annual_interest_rate: Decimal
    origination_fee_rate: Decimal = Decimal("0")


class DevelopmentRequest(ApiModel):
    """Construction, refinance, and stabilized-hold inputs for one project."""

    construction: ConstructionLoanRequest
    operating: OperatingAssumptionsRequest
    stabilization_cap_rate: Decimal
    permanent_loan_to_value: Decimal
    permanent_interest_rate: Decimal
    permanent_amortization_years: int = Field(ge=1)
    exit_cap_rate: Decimal
    selling_cost_rate: Decimal
    refinance_cost_rate: Decimal = Decimal("0")


class SavedSensitivityRequest(SavedMaximumPriceRequest):
    """Solver constraints for an already-persisted assumption set."""
