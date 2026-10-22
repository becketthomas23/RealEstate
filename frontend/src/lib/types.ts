/** API contracts shared by the deal list and the deal workspace. */

export type SensitivityKey =
  | "rent_growth_rate"
  | "exit_cap_rate"
  | "vacancy_rate"
  | "expense_growth_rate"
  | "annual_interest_rate";

export const SENSITIVITY_LABELS: Record<SensitivityKey, string> = {
  rent_growth_rate: "Rent growth",
  exit_cap_rate: "Exit cap rate",
  vacancy_rate: "Vacancy",
  expense_growth_rate: "Expense growth",
  annual_interest_rate: "Interest rate",
};

export type ConfidenceLevel = "low" | "medium" | "high";
export type Distribution = "uniform" | "triangular" | "normal";

/** Form state: strings as typed, decimal rates stored as decimals. */
export type DealForm = {
  purchase_price: string;
  closing_cost_rate: string;
  loan_to_value: string;
  annual_interest_rate: string;
  amortization_years: string;
  exit_cap_rate: string;
  selling_cost_rate: string;
  current_potential_gross_income: string;
  current_operating_expenses: string;
  vacancy_rate: string;
  rent_growth_rate: string;
  annual_rent_growth_schedule: string;
  expense_growth_rate: string;
  hold_period_years: string;
  growth_convention: "current" | "forward";
  target_levered_irr: string;
  minimum_dscr: string;
};

export type OperatingInputs = {
  current_potential_gross_income: string;
  current_operating_expenses: string;
  vacancy_rate: string;
  rent_growth_rate: string;
  expense_growth_rate: string;
  hold_period_years: string | number;
  annual_rent_growth_rates?: string[] | null;
  apply_growth_in_year_one?: boolean;
};

export type UnderwritingInputs = {
  purchase_price: string;
  closing_cost_rate: string;
  loan_to_value: string;
  annual_interest_rate: string;
  amortization_years: string | number;
  exit_cap_rate: string;
  selling_cost_rate: string;
  operating: OperatingInputs;
};

export type PropertyDetail = {
  name: string | null;
  address: string | null;
  units: number | null;
  rentable_square_feet: string | null;
  year_built: number | null;
  property_class: string | null;
};

export type RentRollLine = {
  unit_type: string;
  units: number;
  average_square_feet: string | null;
  current_monthly_rent: string;
  market_monthly_rent: string | null;
};

export type AmountLine = { category: string; annual_amount: string; note: string | null };

export type SupportingDetail = {
  property: PropertyDetail | null;
  rent_roll: RentRollLine[];
  other_income: AmountLine[];
  operating_expenses: AmountLine[];
  notes: string | null;
};

export const EMPTY_DETAIL: SupportingDetail = { property: null, rent_roll: [], other_income: [], operating_expenses: [], notes: null };

export type WorkbookImportResult = {
  underwriting: UnderwritingInputs;
  supporting_detail: SupportingDetail;
  version: {
    label: string | null;
    source: string | null;
    effective_date: string | null;
    confidence_level: ConfidenceLevel;
    property_type: string | null;
  };
  targets: { target_levered_irr: string | null; minimum_dscr: string | null };
  warnings: string[];
  sources: Record<string, string>;
};

export type RiskFlag = {
  code: string;
  severity: string;
  message: string;
  observed_value: string;
  threshold: string;
};

export type OperatingYear = {
  year: number;
  potential_gross_income: string;
  vacancy_loss: string;
  effective_gross_income: string;
  operating_expenses: string;
  net_operating_income: string;
};

export type DebtYear = {
  year: number;
  beginning_balance: string;
  debt_service: string;
  interest: string;
  principal: string;
  ending_balance: string;
};

export type UnderwritingResult = {
  purchase_price?: string;
  loan_amount?: string;
  closing_costs?: string;
  initial_equity?: string;
  going_in_cap_rate: string;
  debt_yield: string | null;
  terminal_noi: string;
  annual_operating_cash_flows: string[];
  annual_cash_flows: string[];
  operating_projection: OperatingYear[];
  debt_projection: DebtYear[];
  disposition: {
    gross_sale_price: string;
    selling_costs: string;
    net_sale_proceeds_before_debt: string;
    loan_payoff: string;
    net_sale_proceeds_to_equity: string;
  };
  returns: {
    levered_irr: string;
    equity_multiple: string;
    total_equity_contributed: string;
    total_equity_distributed: string;
    minimum_dscr: string | null;
    cash_on_cash_by_year: string[];
    dscr_by_year: string[];
  };
  unlevered?: {
    annual_cash_flows: string[];
    irr: string | null;
    multiple: string;
    total_cost: string;
    profit: string;
  };
  levered_profit?: string;
  annual_debt_yield?: string[] | null;
  risk_flags: RiskFlag[];
};

export type PricingResult = {
  maximum_purchase_price: string;
  recommended_bid_floor: string;
  recommended_bid_ceiling: string;
  iterations: number;
  binding_constraint?: "target_levered_irr" | "minimum_dscr";
  searched_minimum_price?: string;
  searched_maximum_price?: string;
  underwriting: UnderwritingResult;
};

export type SensitivityPoint = {
  label: string;
  value: string | null;
  maximum_purchase_price: string | null;
  error: string | null;
};

export type SensitivityDimension = {
  key: string;
  label: string;
  unit: string;
  points: SensitivityPoint[];
  description?: string | null;
};

export type SensitivityResult = { dimensions: SensitivityDimension[] };

export type GridResult = {
  metric: string;
  scenarios: { values: Record<string, string>; metric_value: string | null; error: string | null }[];
};

export type SimulationSummary = {
  metric: string;
  minimum: string;
  percentile_5?: string;
  percentile_10: string;
  percentile_25?: string;
  percentile_50: string;
  percentile_75?: string;
  percentile_90: string;
  percentile_95?: string;
  maximum: string;
  mean: string;
  standard_deviation?: string;
  probability_meeting_target: string | null;
};

export type DriverCorrelation = {
  first_key: SensitivityKey;
  second_key: SensitivityKey;
  coefficient: string;
};

export type MarketContext = {
  property_type: string;
  value_bucket: string;
  source: string;
  source_as_of_date: string;
  observations: number;
  period_start: string;
  period_end: string;
};

export type HistoricalRange = {
  key: SensitivityKey;
  percentile_10: string;
  percentile_50: string;
  percentile_90: string;
};

export type MarketCalibration = {
  context: MarketContext;
  correlations: DriverCorrelation[];
  driver_ranges: HistoricalRange[];
  warnings: string[];
};

export type DriverImpact = {
  key: SensitivityKey;
  return_correlation: string;
  cash_flow_correlation: string;
  relative_influence: string;
  cash_flow_change_per_100_bps: string;
  irr_change_per_100_bps: string;
  irr_at_low?: string | null;
  irr_at_high?: string | null;
  sampled_low?: string;
  sampled_high?: string;
};

export type RepresentativeCase = {
  label: string;
  levered_irr: string;
  values: Record<string, string>;
};

export type SampledRange = { key: SensitivityKey; distribution: Distribution; minimum: string; mode: string; maximum: string };
export type HistogramBin = { lower: string; upper: string; count: number };

export type SimulationResult = {
  iterations: number;
  seed: number;
  sampled_ranges?: SampledRange[];
  levered_irr: SimulationSummary;
  equity_multiple: SimulationSummary;
  terminal_noi: SimulationSummary;
  net_sale_proceeds: SimulationSummary;
  minimum_dscr?: SimulationSummary | null;
  year_one_cash_on_cash?: SimulationSummary;
  irr_histogram?: HistogramBin[];
  probability_of_loss?: string;
  probability_dscr_below_floor?: string | null;
  probability_negative_cash_flow_year?: string;
  base_case_irr?: string;
  correlations?: DriverCorrelation[];
  driver_impacts?: DriverImpact[];
  market_context?: MarketContext | null;
  downside_case?: RepresentativeCase;
  upside_case?: RepresentativeCase;
};

export type SimulationVariableRequest = {
  key: SensitivityKey;
  confidence_level: ConfidenceLevel;
  confidence_percentage: string;
  distribution: Distribution;
  minimum?: string;
  maximum?: string;
};

export type WaterfallYear = {
  year: number;
  property_cash_flow: string;
  lp_capital_contribution: string;
  accrued_preferred_return?: string;
  return_of_capital_to_lp: string;
  preferred_return_to_lp: string;
  residual_to_lp: string;
  residual_to_sponsor: string;
  lp_distribution: string;
  sponsor_distribution: string;
  unpaid_preferred_return: string;
  unreturned_lp_capital: string;
};

export type WaterfallResult = {
  pay_preferred_return_before_capital?: boolean;
  total_lp_contributed: string;
  total_lp_distributed: string;
  total_sponsor_distributed: string;
  lp_irr: string;
  lp_equity_multiple: string;
  years: WaterfallYear[];
};

export type Deal = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
};

export type DealSummary = Deal & {
  version_count: number;
  latest_version: {
    id: string;
    version: number;
    label: string;
    confidence_level: ConfidenceLevel;
    property_type: string;
    value_bucket: string;
    effective_date: string;
    purchase_price: string | null;
  } | null;
  latest_pricing: {
    run_id: string;
    created_at: string;
    maximum_purchase_price: string | null;
    levered_irr: string | null;
    minimum_dscr: string | null;
    equity_multiple: string | null;
    target_levered_irr: string | null;
    binding_constraint: string | null;
    risk_flag_count: number;
  } | null;
};

export type AssumptionSet = {
  id: string;
  deal_id: string;
  version: number;
  label: string;
  source: string | null;
  effective_date: string;
  confidence_level: ConfidenceLevel;
  property_type: string;
  value_bucket: string;
  underwriting: UnderwritingInputs;
  supporting_detail?: SupportingDetail | null;
  created_at?: string;
};

export type DealDetail = Deal & { assumption_sets: AssumptionSet[] };

export type RunRequest = {
  target_levered_irr?: string;
  minimum_dscr?: string;
  purchase_price?: string | null;
  preferred_return_rate?: string;
  sponsor_residual_share?: string;
  iterations?: number;
};

export type CalculationRun = {
  id: string;
  assumption_set_id: string;
  calculation_type: "maximum_price" | "sensitivity" | "monte_carlo" | "waterfall" | "underwriting";
  created_at: string;
  status: string;
  request?: RunRequest | null;
  result: PricingResult | SensitivityResult | SimulationResult | WaterfallResult | UnderwritingResult | null;
};

export type SavedRun<T> = { calculation_run: CalculationRun; result: T };

export type ScenarioComparison = {
  constraints: { target_levered_irr: string; minimum_dscr: string };
  scenarios: {
    assumption_set_id: string;
    version: number;
    label: string;
    confidence_level: ConfidenceLevel;
    maximum_purchase_price: string | null;
    recommended_bid_floor: string | null;
    recommended_bid_ceiling: string | null;
    levered_irr: string | null;
    minimum_dscr: string | null;
    equity_multiple: string | null;
    risk_flags: RiskFlag[];
    error: string | null;
  }[];
};

export const isPricingResult = (value: CalculationRun["result"]): value is PricingResult =>
  value !== null && "maximum_purchase_price" in value;
export const isSensitivityResult = (value: CalculationRun["result"]): value is SensitivityResult =>
  value !== null && "dimensions" in value;
export const isSimulationResult = (value: CalculationRun["result"]): value is SimulationResult =>
  value !== null && "levered_irr" in value && "iterations" in value;
export const isWaterfallResult = (value: CalculationRun["result"]): value is WaterfallResult =>
  value !== null && "lp_irr" in value && "years" in value;
