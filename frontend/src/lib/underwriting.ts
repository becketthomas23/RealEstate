/** Conversions between the deal form and the API's underwriting contract. */

import type { AssumptionSet, DealForm, UnderwritingInputs } from "./types";

// Illustrative defaults only. They are internally consistent (a 6.5% going-in
// yield against a 6.5% exit cap and 1.5x coverage) so a first solve reads like
// a real deal rather than tripping risk flags out of the box.
export const DEFAULT_FORM: DealForm = {
  purchase_price: "8500000",
  closing_cost_rate: "0.02",
  loan_to_value: "0.60",
  annual_interest_rate: "0.06",
  amortization_years: "30",
  exit_cap_rate: "0.065",
  selling_cost_rate: "0.02",
  current_potential_gross_income: "1000000",
  current_operating_expenses: "400000",
  vacancy_rate: "0.05",
  rent_growth_rate: "0.03",
  annual_rent_growth_schedule: "",
  expense_growth_rate: "0.025",
  hold_period_years: "5",
  growth_convention: "current",
  target_levered_irr: "0.12",
  minimum_dscr: "1.25",
};

export function parseSchedule(text: string): string[] | undefined {
  if (!text.trim()) return undefined;
  return text.split(/[;,\s]+/).filter(Boolean).map((value) => {
    const percentage = Number(value);
    if (!Number.isFinite(percentage)) {
      throw new Error("Annual rent-growth schedule must contain only numbers, separated by commas or spaces.");
    }
    return String(parseFloat((percentage / 100).toPrecision(12)));
  });
}

export function toUnderwritingInputs(form: DealForm): UnderwritingInputs {
  return {
    purchase_price: form.purchase_price,
    closing_cost_rate: form.closing_cost_rate,
    loan_to_value: form.loan_to_value,
    annual_interest_rate: form.annual_interest_rate,
    amortization_years: form.amortization_years,
    exit_cap_rate: form.exit_cap_rate,
    selling_cost_rate: form.selling_cost_rate,
    operating: {
      current_potential_gross_income: form.current_potential_gross_income,
      current_operating_expenses: form.current_operating_expenses,
      vacancy_rate: form.vacancy_rate,
      rent_growth_rate: form.rent_growth_rate,
      annual_rent_growth_rates: parseSchedule(form.annual_rent_growth_schedule),
      expense_growth_rate: form.expense_growth_rate,
      hold_period_years: form.hold_period_years,
      apply_growth_in_year_one: form.growth_convention === "forward",
    },
  };
}

/** Load a saved version's inputs back into the form, keeping the constraints. */
export function formFromInputs(inputs: UnderwritingInputs, current: DealForm): DealForm {
  const { operating, ...property } = inputs;
  const { annual_rent_growth_rates, apply_growth_in_year_one, hold_period_years, ...operatingFields } = operating;
  return {
    ...current,
    ...property,
    amortization_years: String(property.amortization_years),
    ...operatingFields,
    hold_period_years: String(hold_period_years),
    growth_convention: apply_growth_in_year_one ? "forward" : "current",
    annual_rent_growth_schedule:
      annual_rent_growth_rates?.map((value) => String(parseFloat((Number(value) * 100).toPrecision(12)))).join(", ") ?? "",
  };
}

/** Canonical form of the inputs so numerically equal versions compare equal. */
export function normalizeInputs(inputs: UnderwritingInputs) {
  const { operating, ...property } = inputs;
  const { annual_rent_growth_rates, apply_growth_in_year_one, ...rest } = operating;
  const numeric = (value: string | number) => String(Number(value));
  return {
    ...Object.fromEntries(Object.entries(property).map(([key, value]) => [key, numeric(value)])),
    operating: {
      ...Object.fromEntries(Object.entries(rest).map(([key, value]) => [key, numeric(value)])),
      annual_rent_growth_rates: annual_rent_growth_rates?.map(numeric) ?? null,
      apply_growth_in_year_one: Boolean(apply_growth_in_year_one),
    },
  };
}

export type VersionMeta = {
  label: string;
  source: string;
  effective_date: string;
  confidence_level: AssumptionSet["confidence_level"];
  property_type: string;
  value_bucket: string;
};

export function versionUnchanged(saved: AssumptionSet | null, meta: VersionMeta, inputs: UnderwritingInputs): saved is AssumptionSet {
  if (!saved) return false;
  return (
    saved.label === meta.label &&
    (saved.source ?? "") === meta.source &&
    saved.effective_date === meta.effective_date &&
    saved.confidence_level === meta.confidence_level &&
    saved.property_type === meta.property_type &&
    saved.value_bucket === meta.value_bucket &&
    JSON.stringify(normalizeInputs(saved.underwriting)) === JSON.stringify(normalizeInputs(inputs))
  );
}
