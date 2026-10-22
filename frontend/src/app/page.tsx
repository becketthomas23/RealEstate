"use client";

import { FormEvent, ReactNode, useEffect, useState } from "react";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (typeof window !== "undefined" &&
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1"
    ? ""
    : "http://127.0.0.1:8000");
type Form = {
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
type OperatingInputs = Pick<
  Form,
  | "current_potential_gross_income"
  | "current_operating_expenses"
  | "vacancy_rate"
  | "rent_growth_rate"
  | "expense_growth_rate"
  | "hold_period_years"
> & {
  annual_rent_growth_rates?: string[] | null;
  apply_growth_in_year_one?: boolean;
};
type Inputs = Pick<
  Form,
  | "purchase_price"
  | "closing_cost_rate"
  | "loan_to_value"
  | "annual_interest_rate"
  | "amortization_years"
  | "exit_cap_rate"
  | "selling_cost_rate"
> & { operating: OperatingInputs };
type RiskFlag = {
  code: string;
  severity: string;
  message: string;
  observed_value: string;
  threshold: string;
};
type Result = {
  maximum_purchase_price: string;
  recommended_bid_floor: string;
  recommended_bid_ceiling: string;
  iterations: number;
  binding_constraint?: "target_levered_irr" | "minimum_dscr";
  searched_minimum_price?: string;
  searched_maximum_price?: string;
  underwriting: {
    purchase_price?: string;
    loan_amount?: string;
    closing_costs?: string;
    initial_equity?: string;
    going_in_cap_rate: string;
    debt_yield: string | null;
    terminal_noi: string;
    annual_operating_cash_flows: string[];
    annual_cash_flows: string[];
    operating_projection: { year: number; net_operating_income: string }[];
    debt_projection: { year: number; debt_service: string }[];
    disposition: { net_sale_proceeds_to_equity: string };
    returns: {
      levered_irr: string;
      equity_multiple: string;
      minimum_dscr: string | null;
      cash_on_cash_by_year: string[];
    };
    risk_flags: RiskFlag[];
  };
};
type SensitivityPoint = {
  label: string;
  value: string | null;
  maximum_purchase_price: string | null;
  error: string | null;
};
type SensitivityDimension = {
  key: string;
  label: string;
  unit: string;
  points: SensitivityPoint[];
  description?: string | null;
};
type SensitivityResult = { dimensions: SensitivityDimension[] };
type AdvancedSensitivity = {
  scenarios: { values: Record<string, string>; metric_value: string | null }[];
};
type SensitivityKey =
  | "rent_growth_rate"
  | "exit_cap_rate"
  | "vacancy_rate"
  | "expense_growth_rate"
  | "annual_interest_rate";
type SimulationSummary = {
  metric: string;
  minimum: string;
  percentile_10: string;
  percentile_50: string;
  percentile_90: string;
  maximum: string;
  mean: string;
  probability_meeting_target: string | null;
};
type DriverCorrelation = {
  first_key: SensitivityKey;
  second_key: SensitivityKey;
  coefficient: string;
};
type MarketContext = {
  property_type: string;
  value_bucket: string;
  source: string;
  source_as_of_date: string;
  observations: number;
  period_start: string;
  period_end: string;
};
type HistoricalRange = {
  key: SensitivityKey;
  percentile_10: string;
  percentile_50: string;
  percentile_90: string;
};
type MarketCalibration = {
  context: MarketContext;
  correlations: DriverCorrelation[];
  driver_ranges: HistoricalRange[];
  warnings: string[];
};
type DriverImpact = {
  key: SensitivityKey;
  return_correlation: string;
  cash_flow_correlation: string;
  relative_influence: string;
  cash_flow_change_per_100_bps: string;
  irr_change_per_100_bps: string;
};
type RepresentativeCase = {
  label: string;
  levered_irr: string;
  values: Record<SensitivityKey, string>;
};
type MonteCarloResult = {
  iterations: number;
  seed: number;
  levered_irr: SimulationSummary;
  equity_multiple: SimulationSummary;
  terminal_noi: SimulationSummary;
  net_sale_proceeds: SimulationSummary;
  correlations?: DriverCorrelation[];
  driver_impacts?: DriverImpact[];
  market_context?: MarketContext | null;
  downside_case?: RepresentativeCase;
  upside_case?: RepresentativeCase;
};
type WaterfallResult = {
  pay_preferred_return_before_capital?: boolean;
  total_lp_contributed: string;
  total_lp_distributed: string;
  total_sponsor_distributed: string;
  lp_irr: string;
  lp_equity_multiple: string;
  years: {
    year: number;
    lp_distribution: string;
    sponsor_distribution: string;
    unpaid_preferred_return: string;
    unreturned_lp_capital: string;
  }[];
};
type Deal = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
};
type Set = {
  id: string;
  deal_id: string;
  version: number;
  label: string;
  source: string | null;
  effective_date: string;
  confidence_level: "low" | "medium" | "high";
  property_type: string;
  value_bucket: string;
  underwriting: Inputs;
};
type DealDetail = Deal & { assumption_sets: Set[] };
type Run = {
  id: string;
  calculation_type: string;
  created_at: string;
  result:
    | Result
    | SensitivityResult
    | MonteCarloResult
    | WaterfallResult
    | null;
  request?: Partial<Pick<Form, "target_levered_irr" | "minimum_dscr">> & {
    purchase_price?: string | null;
  };
};
type SavedCalculation = { calculation_run: Run; result: Result };
type SavedSensitivity = { calculation_run: Run; result: SensitivityResult };
type SavedAnalysis<T> = { calculation_run: Run; result: T };

// Illustrative defaults only. They are internally consistent (a 6.5% going-in
// yield against a 6.5% exit cap and 1.5x coverage) so the first solve reads
// like a real deal rather than tripping risk flags out of the box.
const initial: Form = {
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
// Display a stored decimal rate as a percentage without binary float noise
// (0.07 * 100 is 7.000000000000001 in JavaScript).
const toPercentText = (decimalRate: string) =>
  decimalRate === "" ? "" : String(parseFloat((Number(decimalRate) * 100).toPrecision(12)));
const fromPercentText = (percentText: string) =>
  percentText === "" ? "" : String(parseFloat((Number(percentText) / 100).toPrecision(12)));
const percent2 = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const constraintLabel = (key: Result["binding_constraint"]) =>
  key === "minimum_dscr" ? "minimum DSCR" : "target IRR";
const severityStyle = (severity: string) =>
  severity === "critical"
    ? "border-red-200 bg-red-50 text-red-900"
    : "border-amber-200 bg-amber-50 text-amber-900";
const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
const percent = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const today = () => new Date().toISOString().slice(0, 10);
const valueBucketFor = (purchasePrice: string) => {
  const value = Number(purchasePrice);
  if (!Number.isFinite(value) || value <= 0) return "Custom";
  if (value < 1_000_000) return "Under $1M";
  if (value < 5_000_000) return "$1M-$5M";
  if (value < 10_000_000) return "$5M-$10M";
  if (value < 25_000_000) return "$10M-$25M";
  if (value < 50_000_000) return "$25M-$50M";
  return "$50M+";
};
const simulationDriverBase = (form: Form, key: SensitivityKey) =>
  Number(form[key]);
const isSolverResult = (value: Run["result"]): value is Result =>
  value !== null && "maximum_purchase_price" in value;
const isSensitivityResult = (
  value: Run["result"],
): value is SensitivityResult => value !== null && "dimensions" in value;
const isSimulationResult = (value: Run["result"]): value is MonteCarloResult =>
  value !== null && "levered_irr" in value && "iterations" in value;
const isWaterfallResult = (value: Run["result"]): value is WaterfallResult =>
  value !== null && "lp_irr" in value && "years" in value;

function toUnderwritingInputs(form: Form): Inputs {
  const annual_rent_growth_rates = form.annual_rent_growth_schedule.trim()
    ? form.annual_rent_growth_schedule.split(/[;,\s]+/).map((value) => {
        const percentage = Number(value);
        if (!Number.isFinite(percentage))
          throw new Error(
            "Annual rent-growth schedule must contain only numbers, separated by commas or spaces.",
          );
        return String(percentage / 100);
      })
    : undefined;
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
      annual_rent_growth_rates,
      expense_growth_rate: form.expense_growth_rate,
      hold_period_years: form.hold_period_years,
      apply_growth_in_year_one: form.growth_convention === "forward",
    },
  };
}
function sameInputs(left: unknown, right: unknown) {
  return JSON.stringify(left) === JSON.stringify(right);
}
function normalizeInputs(inputs: Inputs) {
  const { operating, ...property } = inputs;
  const { annual_rent_growth_rates, apply_growth_in_year_one, ...rest } = operating;
  const numeric = (value: string) => String(Number(value));
  return {
    ...Object.fromEntries(Object.entries(property).map(([key, value]) => [key, numeric(value)])),
    operating: {
      ...Object.fromEntries(Object.entries(rest).map(([key, value]) => [key, numeric(String(value))])),
      annual_rent_growth_rates: annual_rent_growth_rates?.map(numeric) ?? null,
      apply_growth_in_year_one: Boolean(apply_growth_in_year_one),
    },
  };
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData =
    typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(API_URL + path, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof data === "object" && data !== null && "detail" in data
        ? (data as { detail: unknown }).detail
        : null;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) =>
          typeof item === "object" && item !== null && "msg" in item
            ? (item as { msg: unknown }).msg
            : null,
        )
        .filter((message): message is string => typeof message === "string");
      if (messages.length) throw new Error(messages.join(" "));
    }
    throw new Error(
      typeof detail === "string"
        ? detail
        : "The request could not be completed.",
    );
  }
  return data as T;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-t border-stone-100 py-6 first:border-t-0 first:pt-0">
      <h3 className="mb-4 text-sm font-semibold text-stone-900">{title}</h3>
      {children}
    </section>
  );
}
function Field({
  label,
  name,
  form,
  setForm,
  suffix,
  negative,
}: {
  label: string;
  name: keyof Form;
  form: Form;
  setForm: (form: Form) => void;
  suffix?: string;
  negative?: boolean;
}) {
  const percentage = suffix === "rate";
  const value = percentage ? toPercentText(form[name]) : form[name];
  return (
    <label className="block text-sm font-medium text-stone-700">
      {label}
      <span className="relative mt-1.5 block">
        <input
          type="number"
          step="any"
          min={negative ? undefined : "0"}
          required
          value={value}
          onChange={(event) => {
            const raw = event.target.value;
            setForm({
              ...form,
              [name]: percentage ? fromPercentText(raw) : raw,
            });
          }}
          className="w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 text-base outline-none transition focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
        />
        {suffix && (
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-stone-500">
            {percentage ? "%" : suffix}
          </span>
        )}
      </span>
    </label>
  );
}

function CashFlowSchedule({
  underwriting,
}: {
  underwriting: Result["underwriting"];
}) {
  const finalIndex = underwriting.annual_cash_flows.length - 1;
  const firstOperatingCashFlow = Number(
    underwriting.annual_operating_cash_flows[0],
  );
  const finalOperatingCashFlow = Number(
    underwriting.annual_operating_cash_flows[finalIndex],
  );
  const finalTotalCashFlow = Number(underwriting.annual_cash_flows[finalIndex]);
  const exitProceeds = Number(
    underwriting.disposition.net_sale_proceeds_to_equity,
  );
  return (
    <div className="mt-7">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold">Cash flow outlook</h2>
          <p className="mt-1 text-xs leading-5 text-stone-400">
            Recurring cash flow is shown by year. Exit proceeds are separated so
            terminal value does not obscure operations.
          </p>
        </div>
        <span className="rounded-full bg-white/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-emerald-200">
          {underwriting.operating_projection.length}-year hold
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
        <div className="rounded-lg bg-white/5 p-3">
          <p className="text-stone-400">Year 1 recurring CF</p>
          <p className="mt-1 font-semibold text-white">
            {money.format(firstOperatingCashFlow)}
          </p>
        </div>
        <div className="rounded-lg bg-white/5 p-3">
          <p className="text-stone-400">Terminal recurring CF</p>
          <p className="mt-1 font-semibold text-white">
            {money.format(finalOperatingCashFlow)}
          </p>
        </div>
        <div className="rounded-lg bg-white/5 p-3">
          <p className="text-stone-400">Net exit proceeds</p>
          <p className="mt-1 font-semibold text-emerald-200">
            {money.format(exitProceeds)}
          </p>
        </div>
        <div className="rounded-lg bg-emerald-950/60 p-3 ring-1 ring-emerald-400/20">
          <p className="text-emerald-200">Final-year total CF</p>
          <p className="mt-1 font-semibold text-emerald-100">
            {money.format(finalTotalCashFlow)}
          </p>
        </div>
      </div>
      <div className="mt-3 overflow-x-auto rounded-xl border border-white/10">
        <table className="w-full min-w-[470px] text-left text-xs">
          <thead className="bg-white/5 text-stone-300">
            <tr>
              <th className="px-3 py-2 font-medium">Year</th>
              <th className="px-3 py-2 text-right font-medium">NOI</th>
              <th className="px-3 py-2 text-right font-medium">Debt service</th>
              <th className="px-3 py-2 text-right font-medium">Recurring CF</th>
              <th className="px-3 py-2 text-right font-medium">Cash-on-cash</th>
            </tr>
          </thead>
          <tbody>
            {underwriting.operating_projection.map((year, index) => {
              const isExitYear = index === finalIndex;
              return (
                <tr
                  className={
                    "border-t border-white/10 " +
                    (isExitYear ? "bg-emerald-950/30" : "")
                  }
                  key={year.year}
                >
                  <td className="px-3 py-2.5 font-medium text-stone-200">
                    {year.year}
                    {isExitYear && (
                      <span className="ml-1.5 rounded bg-emerald-400/15 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-emerald-200">
                        Exit
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    {money.format(Number(year.net_operating_income))}
                  </td>
                  <td className="px-3 py-2.5 text-right text-stone-300">
                    {money.format(
                      Number(underwriting.debt_projection[index].debt_service),
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-right font-semibold text-emerald-200">
                    {money.format(
                      Number(underwriting.annual_operating_cash_flows[index]),
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    {percent.format(
                      Number(underwriting.returns.cash_on_cash_by_year[index]),
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Home() {
  const [form, setForm] = useState<Form>(initial);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [deal, setDeal] = useState<DealDetail | null>(null);
  const [activeSet, setActiveSet] = useState<Set | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityResult | null>(
    null,
  );
  const [twoWay, setTwoWay] = useState<AdvancedSensitivity | null>(null);
  const [simulation, setSimulation] = useState<MonteCarloResult | null>(null);
  const [simulationDrivers, setSimulationDrivers] = useState<SensitivityKey[]>([
    "rent_growth_rate",
    "exit_cap_rate",
    "vacancy_rate",
  ]);
  const [simulationConfidence, setSimulationConfidence] = useState<
    "low" | "medium" | "high"
  >("medium");
  const [simulationIterations, setSimulationIterations] = useState("1000");
  const [marketCalibration, setMarketCalibration] =
    useState<MarketCalibration | null>(null);
  const [marketFile, setMarketFile] = useState<File | null>(null);
  const [marketPropertyType, setMarketPropertyType] = useState("Multifamily");
  const [marketValueBucket, setMarketValueBucket] = useState("$1M-$5M");
  const [marketSource, setMarketSource] = useState(
    "User-provided aggregate market history",
  );
  const [marketSourceAsOfDate, setMarketSourceAsOfDate] = useState(today);
  const [waterfall, setWaterfall] = useState<WaterfallResult | null>(null);
  const [preferredReturn, setPreferredReturn] = useState("0.08");
  const [sponsorShare, setSponsorShare] = useState("0.20");
  const [prefBeforeCapital, setPrefBeforeCapital] = useState(true);
  const [twoWayX, setTwoWayX] = useState<SensitivityKey>("rent_growth_rate");
  const [twoWayY, setTwoWayY] = useState<SensitivityKey>("exit_cap_rate");
  const [dealName, setDealName] = useState("New acquisition");
  const [label, setLabel] = useState("Base case");
  const [source, setSource] = useState("");
  const [effectiveDate, setEffectiveDate] = useState(today);
  const [confidence, setConfidence] =
    useState<Set["confidence_level"]>("medium");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const version = activeSet ? "v" + activeSet.version : "Unsaved";
  const fields = (items: Array<[string, keyof Form, string?, boolean?]>) => (
    <div className="grid gap-4 sm:grid-cols-2">
      {items.map(([labelText, name, suffix, negative]) => (
        <Field
          key={name}
          label={labelText}
          name={name}
          form={form}
          setForm={setForm}
          suffix={suffix}
          negative={negative}
        />
      ))}
    </div>
  );

  useEffect(() => {
    void refreshDeals();
  }, []);
  async function refreshDeals() {
    try {
      setDeals(await api<Deal[]>("/v1/deals"));
    } catch {
      setError(
        "Unable to reach the backend. Start it, then refresh this page.",
      );
    }
  }
  function applySet(saved: Set) {
    setActiveSet(saved);
    setLabel(saved.label);
    setSource(saved.source ?? "");
    setEffectiveDate(saved.effective_date);
    setConfidence(saved.confidence_level);
    setMarketPropertyType(saved.property_type);
    setMarketValueBucket(saved.value_bucket);
    const { operating, ...property } = saved.underwriting;
    const { annual_rent_growth_rates, apply_growth_in_year_one, ...operatingFields } =
      operating;
    setForm((current) => ({
      ...current,
      ...property,
      ...operatingFields,
      growth_convention: apply_growth_in_year_one ? "forward" : "current",
      annual_rent_growth_schedule:
        annual_rent_growth_rates
          ?.map((value) => String(Number(value) * 100))
          .join(", ") ?? "",
    }));
  }
  async function history(id: string, showLatest = false) {
    const found = await api<Run[]>(
      "/v1/assumption-sets/" + id + "/calculation-runs",
    );
    setRuns(found);
    if (showLatest) {
      setResult(null);
      setSensitivity(null);
      setSimulation(null);
      setWaterfall(null);
      const latestSolver = found.find((run) => isSolverResult(run.result));
      const latestSensitivity = found.find((run) =>
        isSensitivityResult(run.result),
      );
      const latestSimulation = found.find((run) =>
        isSimulationResult(run.result),
      );
      const latestWaterfall = found.find((run) =>
        isWaterfallResult(run.result),
      );
      if (latestSolver && isSolverResult(latestSolver.result)) {
        setResult(latestSolver.result);
        if (latestSolver.request) {
          const { target_levered_irr, minimum_dscr } = latestSolver.request;
          setForm((current) => ({
            ...current,
            ...(target_levered_irr ? { target_levered_irr } : {}),
            ...(minimum_dscr ? { minimum_dscr } : {}),
          }));
        }
      }
      if (latestSensitivity && isSensitivityResult(latestSensitivity.result))
        setSensitivity(latestSensitivity.result);
      if (latestSimulation && isSimulationResult(latestSimulation.result))
        setSimulation(latestSimulation.result);
      if (latestWaterfall && isWaterfallResult(latestWaterfall.result))
        setWaterfall(latestWaterfall.result);
    }
  }
  function newDeal() {
    setDeal(null);
    setActiveSet(null);
    setRuns([]);
    setResult(null);
    setSensitivity(null);
    setTwoWay(null);
    setSimulation(null);
    setWaterfall(null);
    setForm(initial);
    setDealName("New acquisition");
    setLabel("Base case");
    setSource("");
    setEffectiveDate(today());
    setConfidence("medium");
    setMarketPropertyType("Multifamily");
    setMarketValueBucket(valueBucketFor(initial.purchase_price));
    setMarketSource("User-provided aggregate market history");
    setMarketSourceAsOfDate(today());
    setError(null);
    setNotice(null);
  }
  async function openDeal(id: string) {
    if (!id) return newDeal();
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const opened = await api<DealDetail>("/v1/deals/" + id);
      setDeal(opened);
      setDealName(opened.name);
      const newest = opened.assumption_sets[0] ?? null;
      setActiveSet(newest);
      if (newest) {
        applySet(newest);
        await history(newest.id, true);
      } else {
        setRuns([]);
        setResult(null);
      }
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to open the saved deal.",
      );
    } finally {
      setLoading(false);
    }
  }
  async function openSet(saved: Set) {
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      applySet(saved);
      await history(saved.id, true);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load calculation history.",
      );
    } finally {
      setLoading(false);
    }
  }
  async function saveAndSolve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      // Parse the locally entered schedule before creating a deal so a typo
      // cannot leave an empty deal record in the audit trail.
      const underwriting = toUnderwritingInputs(form);
      let current = deal;
      if (!current) {
        const created = await api<Deal>("/v1/deals", {
          method: "POST",
          body: JSON.stringify({ name: dealName }),
        });
        current = { ...created, assumption_sets: [] };
        setDeal(current);
      }
      const { target_levered_irr, minimum_dscr } = form;
      // Re-solving with identical inputs and metadata reuses the active
      // version instead of cluttering the audit trail with duplicates.
      const unchanged =
        activeSet &&
        activeSet.deal_id === current.id &&
        activeSet.label === label &&
        (activeSet.source ?? "") === source &&
        activeSet.effective_date === effectiveDate &&
        activeSet.confidence_level === confidence &&
        activeSet.property_type === marketPropertyType &&
        activeSet.value_bucket === marketValueBucket &&
        sameInputs(normalizeInputs(activeSet.underwriting), normalizeInputs(underwriting));
      const saved = unchanged
        ? activeSet
        : await api<Set>("/v1/deals/" + current.id + "/assumption-sets", {
            method: "POST",
            body: JSON.stringify({
              label,
              source: source || null,
              effective_date: effectiveDate,
              confidence_level: confidence,
              property_type: marketPropertyType,
              value_bucket: marketValueBucket,
              underwriting,
            }),
          });
      const calculation = await api<SavedCalculation>(
        "/v1/assumption-sets/" + saved.id + "/maximum-price",
        {
          method: "POST",
          body: JSON.stringify({ target_levered_irr, minimum_dscr }),
        },
      );
      const updated = await api<DealDetail>("/v1/deals/" + current.id);
      setDeal(updated);
      applySet(saved);
      setResult(calculation.result);
      setSensitivity(null);
      setTwoWay(null);
      setSimulation(null);
      setWaterfall(null);
      await history(saved.id);
      await refreshDeals();
      setNotice(
        (unchanged
          ? "Inputs unchanged; re-solved " + current.name + " v" + saved.version
          : "Saved " + current.name + " v" + saved.version) +
          " and recorded the solver run.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The calculation could not be completed.",
      );
    } finally {
      setLoading(false);
    }
  }
  async function calculateSensitivity() {
    if (!activeSet) return;
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const { target_levered_irr, minimum_dscr } = form;
      const calculation = await api<SavedSensitivity>(
        "/v1/assumption-sets/" + activeSet.id + "/sensitivities",
        {
          method: "POST",
          body: JSON.stringify({ target_levered_irr, minimum_dscr }),
        },
      );
      setSensitivity(calculation.result);
      await history(activeSet.id);
      setNotice(
        "Saved the one-way price sensitivity analysis for " + version + ".",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The sensitivity analysis could not be completed.",
      );
    } finally {
      setLoading(false);
    }
  }
  async function calculateTwoWay() {
    setLoading(true);
    setError(null);
    try {
      if (twoWayX === twoWayY)
        throw new Error("Choose two different sensitivity drivers.");
      if (!result)
        throw new Error("Solve the maximum price before running sensitivity.");
      const base = (key: SensitivityKey) =>
        Number(
          key === "annual_interest_rate"
            ? form.annual_interest_rate
            : key === "exit_cap_rate"
              ? form.exit_cap_rate
              : key === "vacancy_rate"
                ? form.vacancy_rate
                : key === "expense_growth_rate"
                  ? form.expense_growth_rate
                  : form.rent_growth_rate,
        );
      const points = (key: SensitivityKey) => {
        const value = base(key),
          step = key === "exit_cap_rate" ? 0.005 : 0.01;
        return [
          Math.max(key === "exit_cap_rate" ? 0.0001 : 0, value - step),
          value,
          value + step,
        ];
      };
      const underwriting = toUnderwritingInputs(form);
      underwriting.purchase_price = result.maximum_purchase_price;
      setTwoWay(
        await api<AdvancedSensitivity>("/v1/advanced-sensitivities", {
          method: "POST",
          body: JSON.stringify({
            underwriting,
            dimensions: [
              { key: twoWayX, values: points(twoWayX) },
              { key: twoWayY, values: points(twoWayY) },
            ],
            metric: "levered_irr",
          }),
        }),
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Two-way sensitivity failed.",
      );
    } finally {
      setLoading(false);
    }
  }
  function toggleSimulationDriver(key: SensitivityKey) {
    setSimulationDrivers((current) =>
      current.includes(key)
        ? current.filter((item) => item !== key)
        : [...current, key],
    );
  }
  async function previewMarketCalibration() {
    if (!marketFile) {
      setError("Choose an aggregate historical market CSV first.");
      return;
    }
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const data = new FormData();
      data.append("file", marketFile);
      data.append("property_type", marketPropertyType);
      data.append("value_bucket", marketValueBucket);
      data.append("source", marketSource);
      data.append("source_as_of_date", marketSourceAsOfDate);
      const calibration = await api<MarketCalibration>(
        "/v1/market-calibrations/preview",
        { method: "POST", body: data },
      );
      setMarketCalibration(calibration);
      setNotice(
        "Loaded " +
          calibration.context.observations +
          " historical periods for " +
          calibration.context.property_type +
          " · " +
          calibration.context.value_bucket +
          ". The source data was not saved.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Market calibration could not be created.",
      );
    } finally {
      setLoading(false);
    }
  }
  async function calculateSimulation() {
    if (!activeSet || !simulationDrivers.length) {
      setError(
        !activeSet
          ? "Save a version before running a risk simulation."
          : "Select at least one risk driver for the simulation.",
      );
      return;
    }
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const correlations =
        marketCalibration?.correlations.filter(
          (item) =>
            simulationDrivers.includes(item.first_key) &&
            simulationDrivers.includes(item.second_key),
        ) ?? [];
      const calibratedBounds = (key: SensitivityKey) => {
        const historical = marketCalibration?.driver_ranges.find(
          (item) => item.key === key,
        );
        if (!historical) return {};
        const base = simulationDriverBase(form, key);
        let minimum =
          base +
          Number(historical.percentile_10) -
          Number(historical.percentile_50);
        let maximum =
          base +
          Number(historical.percentile_90) -
          Number(historical.percentile_50);
        if (key === "exit_cap_rate") minimum = Math.max(minimum, 0.0001);
        if (key === "vacancy_rate" || key === "annual_interest_rate")
          minimum = Math.max(minimum, 0);
        maximum = Math.min(maximum, 0.9999);
        return minimum < maximum
          ? { minimum: String(minimum), maximum: String(maximum) }
          : {};
      };
      const calculation = await api<SavedAnalysis<MonteCarloResult>>(
        "/v1/assumption-sets/" + activeSet.id + "/monte-carlo",
        {
          method: "POST",
          body: JSON.stringify({
            variables: simulationDrivers.map((key) => ({
              key,
              confidence_level: simulationConfidence,
              confidence_percentage: "50",
              ...calibratedBounds(key),
            })),
            iterations: Number(simulationIterations),
            seed: 42,
            target_levered_irr: form.target_levered_irr,
            correlations,
            market_context: marketCalibration?.context ?? null,
            purchase_price: result?.maximum_purchase_price ?? null,
          }),
        },
      );
      setSimulation(calculation.result);
      await history(activeSet.id);
      setNotice(
        "Saved a seeded " +
          calculation.result.iterations +
          "-case return simulation for " +
          version +
          ".",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Monte Carlo analysis failed.",
      );
    } finally {
      setLoading(false);
    }
  }
  async function calculateWaterfall() {
    if (!activeSet) {
      setError("Save a version before running a waterfall.");
      return;
    }
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const calculation = await api<SavedAnalysis<WaterfallResult>>(
        "/v1/assumption-sets/" + activeSet.id + "/waterfall",
        {
          method: "POST",
          body: JSON.stringify({
            preferred_return_rate: preferredReturn,
            sponsor_residual_share: sponsorShare,
            pay_preferred_return_before_capital: prefBeforeCapital,
            purchase_price: result?.maximum_purchase_price ?? null,
          }),
        },
      );
      setWaterfall(calculation.result);
      await history(activeSet.id);
      setNotice(
        "Saved the LP and sponsor distribution waterfall for " + version + ".",
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Waterfall analysis failed.",
      );
    } finally {
      setLoading(false);
    }
  }
  async function downloadExport(kind: "excel" | "memo", filename: string) {
    setLoading(true);
    setError(null);
    try {
      const underwriting = toUnderwritingInputs(form);
      if (result) underwriting.purchase_price = result.maximum_purchase_price;
      const response = await fetch(API_URL + `/v1/exports/${kind}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...underwriting,
          report: {
            deal_name: deal?.name ?? dealName,
            version_label: activeSet?.label ?? label,
            source: source || null,
            effective_date: effectiveDate,
            confidence_level: confidence,
            analysis_basis: result
              ? "solved maximum supportable price"
              : "reference purchase price entered in the form",
            target_levered_irr: form.target_levered_irr,
            minimum_dscr: form.minimum_dscr,
            maximum_purchase_price: result?.maximum_purchase_price ?? null,
            recommended_bid_floor: result?.recommended_bid_floor ?? null,
            recommended_bid_ceiling: result?.recommended_bid_ceiling ?? null,
            binding_constraint: result?.binding_constraint ?? null,
          },
        }),
      });
      if (!response.ok) throw new Error("Export could not be created.");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Export could not be created.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f5f6f2] px-4 py-5 text-stone-900 sm:px-7 sm:py-8 lg:px-10">
      <div className="mx-auto max-w-[1500px]">
        <header className="mb-6 rounded-2xl border border-stone-200 bg-white px-5 py-5 shadow-sm sm:px-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-emerald-800">
                ● Underwriting workspace
              </p>
              <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Price every deal with a clear audit trail.
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">
                Save an immutable assumption version, solve the maximum
                supportable price, and return to every calculation later.
              </p>
            </div>
            <button
              type="button"
              onClick={newDeal}
              className="self-start rounded-xl border border-stone-300 bg-white px-4 py-2.5 text-sm font-semibold text-stone-700 transition hover:border-emerald-700 hover:text-emerald-800"
            >
              + New deal
            </button>
          </div>
        </header>
        <div className="mb-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
          <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm sm:flex sm:items-center sm:gap-4">
            <label className="block flex-1 text-xs font-bold uppercase tracking-[0.12em] text-stone-500">
              Open saved deal
              <select
                aria-label="Open saved deal"
                value={deal?.id ?? ""}
                onChange={(event) => void openDeal(event.target.value)}
                className="mt-2 w-full rounded-xl border border-stone-300 bg-stone-50 px-3 py-2.5 text-sm font-medium text-stone-800 outline-none focus:border-emerald-700"
              >
                <option value="">Create a new deal</option>
                {deals.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            {deal && (
              <div className="mt-4 border-t border-stone-100 pt-4 text-xs text-stone-500 sm:mt-0 sm:border-l sm:border-t-0 sm:pl-4 sm:pt-0">
                <strong className="mr-2 rounded-lg bg-stone-100 px-2 py-1 text-stone-700">
                  {version}
                </strong>
                Immutable versions keep every decision traceable.
              </div>
            )}
          </div>
          <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-5 py-4 text-sm text-emerald-950">
            <p className="font-semibold">
              {deal ? deal.name : "New deal workspace"}
            </p>
            <p className="mt-1 text-xs text-emerald-800">
              {deal
                ? deal.assumption_sets.length + " saved versions"
                : "Nothing is saved until you solve."}
            </p>
          </div>
        </div>
        <div className="grid gap-7 xl:grid-cols-[minmax(0,1fr)_minmax(430px,0.85fr)]">
          <form
            onSubmit={saveAndSolve}
            className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-7"
          >
            <div className="mb-6 flex justify-between">
              <div>
                <h2 className="text-lg font-semibold">Deal assumptions</h2>
                <p className="mt-1 text-sm text-stone-500">
                  Enter all rates as percentages: enter 5 for 5%.
                </p>
              </div>
              <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-stone-600">
                {version}
              </span>
            </div>
            <Section title="Version details">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm font-medium text-stone-700">
                  Deal name
                  <input
                    value={dealName}
                    onChange={(event) => setDealName(event.target.value)}
                    disabled={Boolean(deal)}
                    required
                    className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700 disabled:bg-stone-100"
                  />
                </label>
                <label className="block text-sm font-medium text-stone-700">
                  Version label
                  <input
                    value={label}
                    onChange={(event) => setLabel(event.target.value)}
                    required
                    className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700"
                  />
                </label>
                <label className="block text-sm font-medium text-stone-700">
                  Source or document reference
                  <input
                    value={source}
                    onChange={(event) => setSource(event.target.value)}
                    placeholder="e.g. Broker OM, public record, analyst estimate"
                    required
                    className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700"
                  />
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="block text-sm font-medium text-stone-700">
                    Effective date
                    <input
                      type="date"
                      value={effectiveDate}
                      onChange={(event) => setEffectiveDate(event.target.value)}
                      required
                      className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700"
                    />
                  </label>
                  <label className="block text-sm font-medium text-stone-700">
                    Confidence
                    <select
                      value={confidence}
                      onChange={(event) =>
                        setConfidence(
                          event.target.value as Set["confidence_level"],
                        )
                      }
                      className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </label>
                </div>
                <label className="block text-sm font-medium text-stone-700">
                  Property type
                  <input
                    value={marketPropertyType}
                    onChange={(event) =>
                      setMarketPropertyType(event.target.value)
                    }
                    required
                    className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700"
                  />
                </label>
                <label className="block text-sm font-medium text-stone-700">
                  Asset value bucket
                  <span className="ml-2 text-xs font-normal text-stone-500">
                    Suggested: {valueBucketFor(form.purchase_price)}
                  </span>
                  <input
                    value={marketValueBucket}
                    onChange={(event) =>
                      setMarketValueBucket(event.target.value)
                    }
                    required
                    className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700"
                  />
                  <button
                    type="button"
                    onClick={() =>
                      setMarketValueBucket(valueBucketFor(form.purchase_price))
                    }
                    className="mt-1 text-xs font-semibold text-emerald-800 underline"
                  >
                    Use deal price
                  </button>
                </label>
              </div>
            </Section>
            <Section title="Acquisition & exit">
              {fields([
                ["Reference price (asking or guide)", "purchase_price", "USD"],
                ["Closing costs", "closing_cost_rate", "rate"],
                ["Exit cap rate", "exit_cap_rate", "rate"],
                ["Selling costs", "selling_cost_rate", "rate"],
              ])}
              <p className="mt-2 text-xs leading-5 text-stone-500">
                The reference price seeds the solver and is not a constraint.
                The maximum supportable price is solved from the return and
                coverage targets below; every analysis panel then runs at that
                solved price.
              </p>
            </Section>
            <Section title="Operations">
              {fields([
                [
                  "Current potential gross income",
                  "current_potential_gross_income",
                  "USD / yr",
                ],
                [
                  "Current operating expenses",
                  "current_operating_expenses",
                  "USD / yr",
                ],
                ["Vacancy", "vacancy_rate", "rate"],
                ["Rent growth", "rent_growth_rate", "rate", true],
                ["Expense growth", "expense_growth_rate", "rate", true],
                ["Hold period", "hold_period_years", "years"],
              ])}
              <label className="mt-4 block text-sm font-medium text-stone-700">
                Year 1 convention
                <select
                  value={form.growth_convention}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      growth_convention: event.target.value as Form["growth_convention"],
                    })
                  }
                  className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700"
                >
                  <option value="current">
                    Year 1 = current income and expenses; growth starts Year 2
                  </option>
                  <option value="forward">
                    Entered figures are trailing; grow them once before Year 1
                  </option>
                </select>
                <span className="mt-1 block text-xs font-normal text-stone-500">
                  Going-in cap rate is always Year 1 NOI divided by price, so
                  it matches the first row of the pro forma.
                </span>
              </label>
              <label className="mt-4 block text-sm font-medium text-stone-700">
                Annual rent-growth schedule{" "}
                <span className="font-normal text-stone-500">
                  optional; overrides the base rate
                </span>
                <input
                  type="text"
                  value={form.annual_rent_growth_schedule}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      annual_rent_growth_schedule: event.target.value,
                    })
                  }
                  placeholder="e.g. 4, 3, 2, 2, 2"
                  className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 text-base outline-none transition focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                />
                <span className="mt-1 block text-xs font-normal text-stone-500">
                  Enter percentages for each projection year, separated by
                  commas, spaces, or semicolons. If the schedule is shorter than
                  the hold, its final rate continues.
                </span>
              </label>
            </Section>
            <Section title="Financing">
              {fields([
                ["Loan-to-value", "loan_to_value", "rate"],
                ["Interest rate", "annual_interest_rate", "rate"],
                ["Amortization", "amortization_years", "years"],
              ])}
            </Section>
            <Section title="Investment constraints">
              {fields([
                ["Target levered IRR", "target_levered_irr", "rate"],
                ["Minimum DSCR", "minimum_dscr", "x"],
              ])}
              <p className="mt-2 text-xs leading-5 text-stone-500">
                The solver finds the highest price that meets both targets and
                reports which one binds. No search bounds are needed.
              </p>
            </Section>
            {error && (
              <p
                role="alert"
                className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
              >
                {error}
              </p>
            )}
            {notice && (
              <p className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                {notice}
              </p>
            )}
            <button
              disabled={loading}
              className="w-full rounded-xl bg-emerald-800 px-4 py-3.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-900 disabled:cursor-wait disabled:opacity-70"
            >
              {loading
                ? "Saving & solving…"
                : "Save version & solve maximum price"}
            </button>
          </form>
          <aside className="space-y-5 xl:sticky xl:top-6 xl:self-start">
            <section className="overflow-hidden rounded-2xl border border-stone-800 bg-[#16201b] p-5 text-stone-100 shadow-sm sm:p-7">
              {!result ? (
                <div className="flex min-h-72 flex-col justify-center">
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-300">
                    Results
                  </p>
                  <h2 className="mt-3 text-2xl font-semibold">
                    Ready to underwrite.
                  </h2>
                  <p className="mt-3 max-w-sm text-sm leading-6 text-stone-300">
                    Your result is saved automatically with the exact
                    assumptions and constraints used to create it.
                  </p>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-300">
                        Maximum supportable price
                      </p>
                      <p className="mt-3 text-4xl font-semibold tracking-tight">
                        {money.format(Number(result.maximum_purchase_price))}
                      </p>
                    </div>
                    <span className="rounded-lg bg-white/10 px-2.5 py-1.5 text-right text-xs font-semibold text-stone-200">
                      {result.binding_constraint
                        ? "Bound by " + constraintLabel(result.binding_constraint)
                        : result.iterations + " iterations"}
                    </span>
                  </div>
                  <div className="mt-4 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
                    <span className="text-stone-400">Recommended bid range</span>
                    <span className="font-semibold text-emerald-200">
                      {money.format(Number(result.recommended_bid_floor))} –{" "}
                      {money.format(Number(result.recommended_bid_ceiling))}
                    </span>
                    <span className="text-xs text-stone-500">
                      95% of the maximum up to the maximum itself
                    </span>
                  </div>
                  <div className="my-7 grid grid-cols-3 gap-3 border-y border-white/10 py-5 text-center">
                    <div>
                      <p className="text-lg font-semibold text-emerald-300">
                        {percent.format(
                          Number(result.underwriting.returns.levered_irr),
                        )}
                      </p>
                      <p className="mt-1 text-[10px] uppercase tracking-wide text-stone-400">
                        Levered IRR
                      </p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold">
                        {result.underwriting.returns.minimum_dscr === null
                          ? "N/A"
                          : Number(
                              result.underwriting.returns.minimum_dscr,
                            ).toFixed(2) + "x"}
                      </p>
                      <p className="mt-1 text-[10px] uppercase tracking-wide text-stone-400">
                        Min DSCR
                      </p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold">
                        {Number(
                          result.underwriting.returns.equity_multiple,
                        ).toFixed(2)}
                        x
                      </p>
                      <p className="mt-1 text-[10px] uppercase tracking-wide text-stone-400">
                        Equity multiple
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 rounded-xl bg-white/5 p-3 text-xs sm:grid-cols-3">
                    <div>
                      <p className="text-stone-400">Going-in cap rate</p>
                      <p className="mt-1 font-semibold">
                        {percent2.format(Number(result.underwriting.going_in_cap_rate))}
                      </p>
                    </div>
                    <div>
                      <p className="text-stone-400">Debt yield</p>
                      <p className="mt-1 font-semibold">
                        {result.underwriting.debt_yield === null
                          ? "N/A · all-cash"
                          : percent2.format(Number(result.underwriting.debt_yield))}
                      </p>
                    </div>
                    <div>
                      <p className="text-stone-400">Loan amount</p>
                      <p className="mt-1 font-semibold">
                        {money.format(
                          Number(
                            result.underwriting.loan_amount ??
                              Number(result.maximum_purchase_price) * Number(form.loan_to_value),
                          ),
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="text-stone-400">Equity required</p>
                      <p className="mt-1 font-semibold">
                        {money.format(
                          Number(
                            result.underwriting.initial_equity ??
                              Number(result.maximum_purchase_price) *
                                (1 + Number(form.closing_cost_rate) - Number(form.loan_to_value)),
                          ),
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="text-stone-400">Terminal NOI</p>
                      <p className="mt-1 font-semibold">
                        {money.format(Number(result.underwriting.terminal_noi))}
                      </p>
                    </div>
                    <div>
                      <p className="text-stone-400">Net sale proceeds</p>
                      <p className="mt-1 font-semibold">
                        {money.format(
                          Number(
                            result.underwriting.disposition
                              .net_sale_proceeds_to_equity,
                          ),
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="mt-4">
                    <p className="text-xs font-bold uppercase tracking-[0.14em] text-stone-400">
                      Risk flags at the solved price
                    </p>
                    {result.underwriting.risk_flags.length === 0 ? (
                      <p className="mt-2 rounded-lg border border-emerald-400/20 bg-emerald-950/40 px-3 py-2 text-xs text-emerald-100">
                        No rules-based risk flags triggered.
                      </p>
                    ) : (
                      <ul className="mt-2 space-y-2">
                        {result.underwriting.risk_flags.map((flag) => (
                          <li
                            key={flag.code}
                            className={
                              "rounded-lg border px-3 py-2 text-xs " + severityStyle(flag.severity)
                            }
                          >
                            <span className="mr-2 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ring-1 ring-current">
                              {flag.severity}
                            </span>
                            {flag.message}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <CashFlowSchedule underwriting={result.underwriting} />
                </>
              )}
            </section>
            {result && activeSet && (
              <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-base font-semibold">
                      One-way price sensitivity
                    </h2>
                    <p className="mt-1 text-xs leading-5 text-stone-500">
                      Each case changes one assumption and re-solves the maximum
                      price.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void calculateSensitivity()}
                    disabled={loading}
                    className="shrink-0 rounded-lg bg-emerald-800 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-900 disabled:opacity-60"
                  >
                    {loading ? "Running…" : "Run analysis"}
                  </button>
                </div>
                {sensitivity && (
                  <div className="mt-5 space-y-5">
                    {sensitivity.dimensions.map((dimension) => (
                      <div key={dimension.key}>
                        <div className="mb-2 flex items-center justify-between">
                          <h3 className="text-sm font-semibold text-stone-800">
                            {dimension.label}
                          </h3>
                          <span className="text-[10px] uppercase tracking-wide text-stone-500">
                            {dimension.key === "exit_cap_rate"
                              ? "±50 bps"
                              : "±100 bps"}
                          </span>
                        </div>
                        {dimension.description && (
                          <p className="mb-2 text-xs leading-5 text-stone-500">
                            {dimension.description}
                          </p>
                        )}
                        <div className="overflow-hidden rounded-xl border border-stone-200">
                          <table className="w-full text-xs">
                            <thead className="bg-stone-50 text-stone-500">
                              <tr>
                                <th className="px-3 py-2 text-left font-medium">
                                  Case
                                </th>
                                <th className="px-3 py-2 text-right font-medium">
                                  Input
                                </th>
                                <th className="px-3 py-2 text-right font-medium">
                                  Max price
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {dimension.points.map((point) => (
                                <tr
                                  key={point.label}
                                  className="border-t border-stone-100"
                                >
                                  <td className="px-3 py-2 font-medium text-stone-700">
                                    {point.label}
                                  </td>
                                  <td className="px-3 py-2 text-right text-stone-600">
                                    {point.value === null
                                      ? "Scheduled"
                                      : percent.format(Number(point.value))}
                                  </td>
                                  <td className="px-3 py-2 text-right font-semibold text-emerald-800">
                                    {point.maximum_purchase_price
                                      ? money.format(
                                          Number(point.maximum_purchase_price),
                                        )
                                      : "Unavailable"}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}
            {result && (
              <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-semibold">Exports</h2>
                    <p className="mt-1 text-xs text-stone-500">
                      Excel workbook or PDF memo for the solved case (
                      {money.format(Number(result.maximum_purchase_price))}),
                      including the bid range and the deal&apos;s version details.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={loading}
                      onClick={() =>
                        void downloadExport(
                          "excel",
                          "underwriting-cash-flow.xlsx",
                        )
                      }
                      className="rounded-lg border border-stone-300 px-3 py-2 text-xs font-semibold"
                    >
                      Excel model
                    </button>
                    <button
                      type="button"
                      disabled={loading}
                      onClick={() =>
                        void downloadExport("memo", "investment-memo.pdf")
                      }
                      className="rounded-lg bg-emerald-800 px-3 py-2 text-xs font-semibold text-white"
                    >
                      PDF memo
                    </button>
                  </div>
                </div>
              </section>
            )}
            {result && (
              <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-semibold">
                      Two-way sensitivity
                    </h2>
                    <p className="mt-1 text-xs text-stone-500">
                      Choose two drivers. IRR is calculated at the solved
                      maximum price (
                      {money.format(Number(result.maximum_purchase_price))});
                      the center case should match the target IRR.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void calculateTwoWay()}
                    disabled={loading}
                    className="rounded-lg bg-emerald-800 px-3 py-2 text-xs font-semibold text-white"
                  >
                    Run two-way
                  </button>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <label className="text-xs font-semibold text-stone-600">
                    Rows
                    <select
                      value={twoWayX}
                      onChange={(event) =>
                        setTwoWayX(event.target.value as SensitivityKey)
                      }
                      className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-2 py-2 text-sm"
                    >
                      <option value="rent_growth_rate">Rent growth</option>
                      <option value="exit_cap_rate">Exit cap rate</option>
                      <option value="vacancy_rate">Vacancy</option>
                      <option value="expense_growth_rate">
                        Expense growth
                      </option>
                      <option value="annual_interest_rate">
                        Interest rate
                      </option>
                    </select>
                  </label>
                  <label className="text-xs font-semibold text-stone-600">
                    Columns
                    <select
                      value={twoWayY}
                      onChange={(event) =>
                        setTwoWayY(event.target.value as SensitivityKey)
                      }
                      className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-2 py-2 text-sm"
                    >
                      <option value="rent_growth_rate">Rent growth</option>
                      <option value="exit_cap_rate">Exit cap rate</option>
                      <option value="vacancy_rate">Vacancy</option>
                      <option value="expense_growth_rate">
                        Expense growth
                      </option>
                      <option value="annual_interest_rate">
                        Interest rate
                      </option>
                    </select>
                  </label>
                </div>
                {twoWay && (
                  <div className="mt-4 grid grid-cols-3 gap-2">
                    {twoWay.scenarios.map((scenario, index) => (
                      <div
                        key={index}
                        className={
                          "rounded-lg border p-2 text-center text-xs " +
                          (index === 4
                            ? "border-emerald-600 bg-emerald-50"
                            : "border-stone-200")
                        }
                      >
                        <p className="text-stone-500">
                          {percent.format(Number(scenario.values[twoWayX]))} /{" "}
                          {percent.format(Number(scenario.values[twoWayY]))}
                        </p>
                        <p className="mt-1 font-semibold text-emerald-800">
                          {scenario.metric_value
                            ? percent.format(Number(scenario.metric_value))
                            : "-"}
                        </p>
                        {index === 4 && (
                          <p className="mt-1 text-[10px] font-bold uppercase text-emerald-700">
                            Base case
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}
            {result && (
              <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-base font-semibold">
                      Return-risk simulation
                    </h2>
                    <p className="mt-1 text-xs leading-5 text-stone-500">
                      Samples selected inputs across confidence-aware ranges at
                      the solved price ({money.format(Number(result.maximum_purchase_price))}).
                      A loaded market calibration lets drivers move together.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void calculateSimulation()}
                    disabled={loading || !simulationDrivers.length}
                    className="shrink-0 rounded-lg bg-emerald-800 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-900 disabled:opacity-60"
                  >
                    {loading ? "Running…" : "Run simulation"}
                  </button>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <fieldset>
                    <legend className="text-xs font-semibold text-stone-600">
                      Risk drivers
                    </legend>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      {(
                        [
                          ["rent_growth_rate", "Rent growth"],
                          ["exit_cap_rate", "Exit cap"],
                          ["vacancy_rate", "Vacancy"],
                          ["expense_growth_rate", "Expense growth"],
                          ["annual_interest_rate", "Interest rate"],
                        ] as [SensitivityKey, string][]
                      ).map(([key, labelText]) => (
                        <label
                          key={key}
                          className="flex items-center gap-2 text-xs text-stone-700"
                        >
                          <input
                            type="checkbox"
                            checked={simulationDrivers.includes(key)}
                            onChange={() => toggleSimulationDriver(key)}
                            className="accent-emerald-800"
                          />
                          {labelText}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                  <div className="grid grid-cols-2 gap-3">
                    <label className="text-xs font-semibold text-stone-600">
                      Confidence
                      <select
                        value={simulationConfidence}
                        onChange={(event) =>
                          setSimulationConfidence(
                            event.target.value as "low" | "medium" | "high",
                          )
                        }
                        className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-2 py-2 text-sm"
                      >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                      </select>
                    </label>
                    <label className="text-xs font-semibold text-stone-600">
                      Iterations
                      <input
                        type="number"
                        min="100"
                        max="10000"
                        step="100"
                        value={simulationIterations}
                        onChange={(event) =>
                          setSimulationIterations(event.target.value)
                        }
                        className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-2 py-2 text-sm"
                      />
                    </label>
                  </div>
                </div>
                <div className="mt-5 rounded-xl border border-stone-200 bg-stone-50 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-xs font-semibold text-stone-800">
                        Market correlation calibration
                      </h3>
                      <p className="mt-1 text-xs leading-5 text-stone-500">
                        Load aggregate quarterly history by property type and
                        value bucket. The CSV is used to calculate correlations
                        and is not saved. Enter the publisher or preparer and
                        the report as-of or pull date so a saved simulation
                        retains its provenance.
                      </p>
                    </div>
                    <a
                      href={API_URL + "/v1/market-calibrations/template"}
                      className="shrink-0 text-xs font-semibold text-emerald-800 underline"
                    >
                      CSV template
                    </a>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <label className="text-xs font-semibold text-stone-600">
                      Property type
                      <input
                        value={marketPropertyType}
                        onChange={(event) =>
                          setMarketPropertyType(event.target.value)
                        }
                        className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-2 py-2 text-sm"
                      />
                    </label>
                    <label className="text-xs font-semibold text-stone-600">
                      Value bucket
                      <span className="ml-2 normal-case text-stone-500">
                        Suggested: {valueBucketFor(form.purchase_price)}
                      </span>
                      <input
                        value={marketValueBucket}
                        onChange={(event) =>
                          setMarketValueBucket(event.target.value)
                        }
                        className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-2 py-2 text-sm"
                      />
                      <button
                        type="button"
                        onClick={() =>
                          setMarketValueBucket(
                            valueBucketFor(form.purchase_price),
                          )
                        }
                        className="mt-1 text-xs font-semibold text-emerald-800 underline"
                      >
                        Use deal price
                      </button>
                    </label>
                    <label className="text-xs font-semibold text-stone-600">
                      Source or document reference
                      <input
                        value={marketSource}
                        onChange={(event) =>
                          setMarketSource(event.target.value)
                        }
                        required
                        className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-2 py-2 text-sm"
                      />
                    </label>
                    <label className="text-xs font-semibold text-stone-600">
                      Source as-of or pull date
                      <input
                        type="date"
                        value={marketSourceAsOfDate}
                        onChange={(event) =>
                          setMarketSourceAsOfDate(event.target.value)
                        }
                        required
                        className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-2 py-2 text-sm"
                      />
                    </label>
                    <label className="text-xs font-semibold text-stone-600">
                      Aggregate history CSV
                      <input
                        type="file"
                        accept=".csv,text/csv"
                        onChange={(event) =>
                          setMarketFile(event.target.files?.[0] ?? null)
                        }
                        className="mt-1 block w-full text-xs"
                      />
                    </label>
                  </div>
                  <button
                    type="button"
                    onClick={() => void previewMarketCalibration()}
                    disabled={loading || !marketFile || !marketSource.trim() || !marketSourceAsOfDate}
                    className="mt-3 rounded-lg border border-emerald-800 px-3 py-2 text-xs font-semibold text-emerald-800 disabled:opacity-60"
                  >
                    {loading ? "Loading…" : "Load correlations"}
                  </button>
                  {marketCalibration && (
                    <div className="mt-3 rounded-lg bg-emerald-50 p-3 text-xs text-emerald-950">
                      <p className="font-semibold">
                        {marketCalibration.context.property_type} ·{" "}
                        {marketCalibration.context.value_bucket}
                      </p>
                      <p className="mt-1 text-emerald-800">
                        Source: {marketCalibration.context.source} (as of{" "}
                        {marketCalibration.context.source_as_of_date})
                      </p>
                      <p className="mt-1">
                        {marketCalibration.context.observations} periods,{" "}
                        {marketCalibration.context.period_start}–
                        {marketCalibration.context.period_end}. Matching
                        selected drivers will move together, and historical
                        P10/P90 shifts will set the next simulation&apos;s
                        ranges around this deal&apos;s base assumptions.
                      </p>
                      <div className="mt-2 grid grid-cols-1 gap-1 text-emerald-950 sm:grid-cols-2">
                        {marketCalibration.driver_ranges
                          .filter((item) =>
                            simulationDrivers.includes(item.key),
                          )
                          .map((item) => (
                            <p key={item.key}>
                              <span className="font-semibold">
                                {item.key.replaceAll("_", " ")}
                              </span>{" "}
                              · historical P10{" "}
                              {percent.format(Number(item.percentile_10))} / P50{" "}
                              {percent.format(Number(item.percentile_50))} / P90{" "}
                              {percent.format(Number(item.percentile_90))}
                            </p>
                          ))}
                      </div>
                      <div className="mt-2 border-t border-emerald-200 pt-2">
                        <p className="font-semibold">
                          Selected-driver correlations
                        </p>
                        <p className="mt-1 text-emerald-800">
                          Positive values mean the two inputs tended to move
                          together; negative values mean they tended to move in
                          opposite directions.
                        </p>
                        {marketCalibration.correlations
                          .filter(
                            (item) =>
                              simulationDrivers.includes(item.first_key) &&
                              simulationDrivers.includes(item.second_key),
                          )
                          .map((item) => (
                            <p
                              key={item.first_key + item.second_key}
                              className="mt-1"
                            >
                              <span className="capitalize">
                                {item.first_key.replaceAll("_", " ")}
                              </span>{" "}
                              /{" "}
                              <span className="capitalize">
                                {item.second_key.replaceAll("_", " ")}
                              </span>
                              :{" "}
                              <strong>
                                {Number(item.coefficient).toFixed(2)}
                              </strong>
                            </p>
                          ))}
                      </div>
                      {marketCalibration.warnings.map((warning) => (
                        <p
                          key={warning}
                          className="mt-2 rounded-md bg-amber-100 px-2 py-1 text-amber-900"
                        >
                          {warning}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
                {simulation && (
                  <>
                    <div className="mt-5 overflow-hidden rounded-xl border border-stone-200">
                      <table className="w-full text-xs">
                        <thead className="bg-stone-50 text-stone-500">
                          <tr>
                            <th className="px-3 py-2 text-left font-medium">
                              Levered IRR
                            </th>
                            <th className="px-3 py-2 text-right font-medium">
                              P10
                            </th>
                            <th className="px-3 py-2 text-right font-medium">
                              Median
                            </th>
                            <th className="px-3 py-2 text-right font-medium">
                              P90
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td className="px-3 py-3 font-semibold text-stone-800">
                              Meets target{" "}
                              {simulation.levered_irr.probability_meeting_target
                                ? percent.format(
                                    Number(
                                      simulation.levered_irr
                                        .probability_meeting_target,
                                    ),
                                  )
                                : "—"}
                            </td>
                            <td className="px-3 py-3 text-right text-red-700">
                              {percent.format(
                                Number(simulation.levered_irr.percentile_10),
                              )}
                            </td>
                            <td className="px-3 py-3 text-right font-semibold text-emerald-800">
                              {percent.format(
                                Number(simulation.levered_irr.percentile_50),
                              )}
                            </td>
                            <td className="px-3 py-3 text-right text-emerald-800">
                              {percent.format(
                                Number(simulation.levered_irr.percentile_90),
                              )}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    {simulation.downside_case && (
                      <div className="mt-4 rounded-xl border border-red-100 bg-red-50 p-3 text-xs">
                        <p className="font-semibold text-red-900">
                          {simulation.downside_case.label} ·{" "}
                          {percent.format(
                            Number(simulation.downside_case.levered_irr),
                          )}{" "}
                          levered IRR
                        </p>
                        <p className="mt-1 text-red-800">
                          These are driver values that occurred together in one
                          generated downside outcome—not individual worst cases.
                        </p>
                        <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-red-900">
                          {Object.entries(simulation.downside_case.values).map(
                            ([key, value]) => (
                              <span key={key}>
                                {key.replaceAll("_", " ")}:{" "}
                                {percent.format(Number(value))}
                              </span>
                            ),
                          )}
                        </div>
                      </div>
                    )}
                    {simulation.driver_impacts && (
                      <div className="mt-4">
                        <p className="text-xs font-semibold text-stone-700">
                          Driver impact in this deal
                        </p>
                        <p className="mt-1 text-xs text-stone-500">
                          Per 100 bps changes one driver from the base case
                          while holding all other inputs fixed. The correlation
                          columns describe the joint simulation, not a
                          standalone causal forecast. Cash flow is cumulative
                          operating cash flow over the hold and excludes sale
                          proceeds.
                        </p>
                        <div className="mt-2 overflow-x-auto rounded-lg border border-stone-200">
                          <table className="w-full min-w-[560px] text-xs">
                            <thead className="bg-stone-50 text-stone-500">
                              <tr>
                                <th className="px-3 py-2 text-left font-medium">
                                  Driver
                                </th>
                                <th className="px-3 py-2 text-right font-medium">
                                  IRR influence
                                </th>
                                <th className="px-3 py-2 text-right font-medium">
                                  IRR / 100 bps
                                </th>
                                <th className="px-3 py-2 text-right font-medium">
                                  Operating CF / 100 bps
                                </th>
                                <th className="px-3 py-2 text-right font-medium">
                                  CF correlation
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {simulation.driver_impacts.map((item) => (
                                <tr
                                  key={item.key}
                                  className="border-t border-stone-100"
                                >
                                  <td className="px-3 py-2 capitalize text-stone-700">
                                    {item.key.replaceAll("_", " ")}
                                  </td>
                                  <td className="px-3 py-2 text-right font-semibold text-stone-800">
                                    {percent.format(
                                      Number(item.relative_influence),
                                    )}{" "}
                                    ·{" "}
                                    {Number(item.return_correlation) >= 0
                                      ? "with"
                                      : "against"}
                                  </td>
                                  <td className="px-3 py-2 text-right text-stone-800">
                                    {percent.format(
                                      Number(item.irr_change_per_100_bps),
                                    )}
                                  </td>
                                  <td className="px-3 py-2 text-right text-stone-800">
                                    {money.format(
                                      Number(item.cash_flow_change_per_100_bps),
                                    )}
                                  </td>
                                  <td className="px-3 py-2 text-right text-stone-800">
                                    {Number(item.cash_flow_correlation).toFixed(
                                      2,
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </section>
            )}
            {result && (
              <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-base font-semibold">
                      LP / sponsor waterfall
                    </h2>
                    <p className="mt-1 text-xs leading-5 text-stone-500">
                      Allocates the equity cash flow at the solved price (
                      {money.format(Number(result.maximum_purchase_price))}).
                      Pref accrues yearly on outstanding LP capital, including
                      capital-call years.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void calculateWaterfall()}
                    disabled={loading}
                    className="shrink-0 rounded-lg bg-emerald-800 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-900 disabled:opacity-60"
                  >
                    {loading ? "Running…" : "Run waterfall"}
                  </button>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <label className="col-span-2 text-xs font-semibold text-stone-600">
                    Tier order
                    <select
                      value={prefBeforeCapital ? "pref_first" : "capital_first"}
                      onChange={(event) =>
                        setPrefBeforeCapital(event.target.value === "pref_first")
                      }
                      className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-2 py-2 text-sm"
                    >
                      <option value="pref_first">
                        Accrued preferred return, then return of capital, then split
                      </option>
                      <option value="capital_first">
                        Return of capital, then accrued preferred return, then split
                      </option>
                    </select>
                  </label>
                  <label className="text-xs font-semibold text-stone-600">
                    Preferred return
                    <input
                      type="number"
                      min="0"
                      max="99"
                      step="0.1"
                      value={toPercentText(preferredReturn)}
                      onChange={(event) =>
                        setPreferredReturn(fromPercentText(event.target.value))
                      }
                      className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-2 py-2 text-sm"
                    />
                  </label>
                  <label className="text-xs font-semibold text-stone-600">
                    Sponsor residual share
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="1"
                      value={toPercentText(sponsorShare)}
                      onChange={(event) =>
                        setSponsorShare(fromPercentText(event.target.value))
                      }
                      className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-2 py-2 text-sm"
                    />
                  </label>
                </div>
                {waterfall && (
                  <div className="mt-5 grid grid-cols-3 gap-3 rounded-xl bg-stone-50 p-3 text-center text-xs">
                    <div>
                      <p className="font-semibold text-emerald-800">
                        {percent.format(Number(waterfall.lp_irr))}
                      </p>
                      <p className="mt-1 text-stone-500">LP IRR</p>
                    </div>
                    <div>
                      <p className="font-semibold text-stone-800">
                        {Number(waterfall.lp_equity_multiple).toFixed(2)}x
                      </p>
                      <p className="mt-1 text-stone-500">LP multiple</p>
                    </div>
                    <div>
                      <p className="font-semibold text-stone-800">
                        {money.format(
                          Number(waterfall.total_sponsor_distributed),
                        )}
                      </p>
                      <p className="mt-1 text-stone-500">Sponsor proceeds</p>
                    </div>
                  </div>
                )}
              </section>
            )}
            {deal && (
              <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-semibold">Version history</h2>
                    <p className="mt-1 text-xs text-stone-500">
                      Inputs remain editable only as a new version.
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-stone-500">
                    {deal.assumption_sets.length} saved
                  </span>
                </div>
                <div className="mt-4 space-y-2">
                  {deal.assumption_sets.map((saved) => (
                    <button
                      type="button"
                      key={saved.id}
                      onClick={() => void openSet(saved)}
                      className={
                        "w-full rounded-xl border p-3 text-left transition " +
                        (activeSet?.id === saved.id
                          ? "border-emerald-500 bg-emerald-50"
                          : "border-stone-200 hover:bg-stone-50")
                      }
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold">
                          v{saved.version} · {saved.label}
                        </span>
                        <span className="text-[10px] font-bold uppercase text-stone-500">
                          {saved.confidence_level}
                        </span>
                      </div>
                      <p className="mt-1 truncate text-xs text-stone-500">
                        {saved.source || "No source recorded"} ·{" "}
                        {saved.effective_date}
                      </p>
                    </button>
                  ))}
                </div>
                {runs.length > 0 && (
                  <div className="mt-5 border-t border-stone-100 pt-4">
                    <p className="mb-2 text-xs font-bold uppercase tracking-wide text-stone-500">
                      Saved runs for {version}
                    </p>
                    {runs.map((run) => (
                      <button
                        type="button"
                        key={run.id}
                        onClick={() => {
                          if (isSolverResult(run.result)) setResult(run.result);
                          if (isSensitivityResult(run.result))
                            setSensitivity(run.result);
                          if (isSimulationResult(run.result))
                            setSimulation(run.result);
                          if (isWaterfallResult(run.result))
                            setWaterfall(run.result);
                        }}
                        className="mb-2 flex w-full justify-between rounded-lg bg-stone-50 px-3 py-2 text-left text-xs text-stone-700 hover:bg-emerald-50"
                      >
                        <span className="capitalize">
                          {run.calculation_type.replace("_", " ")}
                        </span>
                        <span>
                          {new Date(run.created_at).toLocaleDateString()}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </section>
            )}
          </aside>
        </div>
      </div>
    </main>
  );
}
