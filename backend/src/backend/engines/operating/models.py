"""Input and output contracts for the operating pro-forma engine."""

from dataclasses import dataclass
from decimal import Decimal

from backend.core.validation import ONE, ZERO, require_non_negative, require_positive, require_rate


@dataclass(frozen=True, slots=True)
class OperatingAssumptions:
    """Current (in-place) operating inputs and the growth applied to them.

    ``apply_growth_in_year_one`` controls the Year 1 convention. By default
    Year 1 equals the current income and expenses entered by the analyst and
    growth begins in Year 2, so the going-in cap rate is the current NOI yield.
    Setting it to ``True`` treats the entered values as trailing figures and
    grows them once before Year 1 (a forward-NOI convention).
    """

    current_potential_gross_income: Decimal
    current_operating_expenses: Decimal
    vacancy_rate: Decimal
    rent_growth_rate: Decimal
    expense_growth_rate: Decimal
    hold_period_years: int
    annual_rent_growth_rates: tuple[Decimal, ...] | None = None
    apply_growth_in_year_one: bool = False

    def __post_init__(self) -> None:
        require_positive("current_potential_gross_income", self.current_potential_gross_income)
        require_non_negative("current_operating_expenses", self.current_operating_expenses)
        require_rate("vacancy_rate", self.vacancy_rate)
        require_rate("rent_growth_rate", self.rent_growth_rate, allow_negative=True)
        require_rate("expense_growth_rate", self.expense_growth_rate, allow_negative=True)
        if not 5 <= self.hold_period_years <= 10:
            raise ValueError("hold_period_years must be between 5 and 10")
        if self.annual_rent_growth_rates is not None:
            schedule = tuple(self.annual_rent_growth_rates)
            if not schedule:
                raise ValueError("annual_rent_growth_rates must not be empty when supplied")
            if len(schedule) > self.hold_period_years:
                raise ValueError("annual_rent_growth_rates cannot exceed hold_period_years")
            for rate in schedule:
                require_rate("annual_rent_growth_rates", rate, allow_negative=True)
            object.__setattr__(self, "annual_rent_growth_rates", schedule)

    @property
    def current_noi(self) -> Decimal:
        return self.current_potential_gross_income * (ONE - self.vacancy_rate) - self.current_operating_expenses

    @property
    def first_growth_year(self) -> int:
        return 1 if self.apply_growth_in_year_one else 2

    def growth_periods_through(self, year: int) -> int:
        """Return how many annual growth steps have been applied by ``year``."""
        if year < 1:
            raise ValueError("year must be at least 1")
        return max(year - self.first_growth_year + 1, 0)

    def rent_growth_rate_for_year(self, year: int) -> Decimal:
        """Return the rent growth applied when moving into a projection year.

        Year 1 has no growth unless ``apply_growth_in_year_one`` is set. A
        supplied schedule overrides the base rate in order, starting with the
        first growth year. If the hold or terminal year extends beyond that
        schedule, its final explicit rate is continued. This makes a partially
        entered schedule deterministic while still permitting a single base
        assumption.
        """
        periods = self.growth_periods_through(year)
        if periods == 0:
            return ZERO
        if not self.annual_rent_growth_rates:
            return self.rent_growth_rate
        return self.annual_rent_growth_rates[min(periods - 1, len(self.annual_rent_growth_rates) - 1)]


@dataclass(frozen=True, slots=True)
class OperatingYear:
    year: int
    potential_gross_income: Decimal
    vacancy_loss: Decimal
    effective_gross_income: Decimal
    operating_expenses: Decimal
    net_operating_income: Decimal


@dataclass(frozen=True, slots=True)
class OperatingMonth:
    """Monthly view of the annual operating projection.

    The current stabilized model applies each annual growth assumption at the
    start of its projection year, then allocates that year's annual operating
    amounts evenly across its twelve months.  Monthly values therefore roll up
    exactly to the audited annual pro forma.
    """

    month: int
    year: int
    month_in_year: int
    potential_gross_income: Decimal
    vacancy_loss: Decimal
    effective_gross_income: Decimal
    operating_expenses: Decimal
    net_operating_income: Decimal
