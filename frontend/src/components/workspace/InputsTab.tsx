"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import { API_URL } from "@/lib/api";
import { fromPercentText, money, percent, toPercentText, valueBucketFor } from "@/lib/format";
import { EMPTY_DETAIL, type AmountLine, type DealForm, type RentRollLine, type SupportingDetail } from "@/lib/types";
import { Badge, Banner, Button, Card, Field, NumberField, SectionHeading, Select, TextInput } from "../ui";
import { hasDetail, type Workspace } from "./useDealWorkspace";

type RateKey = Extract<
  keyof DealForm,
  "closing_cost_rate" | "loan_to_value" | "annual_interest_rate" | "exit_cap_rate" | "selling_cost_rate" | "vacancy_rate" | "rent_growth_rate" | "expense_growth_rate" | "target_levered_irr"
>;

export function InputsTab({ workspace }: { workspace: Workspace }) {
  const { form, setForm, meta, setMeta, detail, setDetail, activeSet, busy, saveAndSolve, importFile, dirty, importWarnings, setImportWarnings } = workspace;
  const fileInput = useRef<HTMLInputElement>(null);
  const [showDetail, setShowDetail] = useState(hasDetail(detail));
  const set = (key: keyof DealForm) => (value: string) => setForm({ ...form, [key]: value });
  const setRate = (key: RateKey) => (value: string) => setForm({ ...form, [key]: fromPercentText(value) });
  const rate = (key: RateKey) => toPercentText(form[key]);
  const property = detail.property ?? { name: null, address: null, units: null, rentable_square_feet: null, year_built: null, property_class: null };
  const setProperty = (patch: Partial<SupportingDetail["property"] & object>) => setDetail({ ...detail, property: { ...property, ...patch } });

  const rollUp = useMemo(() => {
    const rent = detail.rent_roll.reduce((sum, line) => sum + Number(line.units || 0) * Number(line.current_monthly_rent || 0) * 12, 0);
    const other = detail.other_income.reduce((sum, line) => sum + Number(line.annual_amount || 0), 0);
    const expenses = detail.operating_expenses.reduce((sum, line) => sum + Number(line.annual_amount || 0), 0);
    const units = detail.rent_roll.reduce((sum, line) => sum + Number(line.units || 0), 0);
    return { income: rent + other, expenses, units, hasIncome: detail.rent_roll.length > 0 || detail.other_income.length > 0, hasExpenses: detail.operating_expenses.length > 0 };
  }, [detail]);
  const incomeDiffers = rollUp.hasIncome && Math.abs(rollUp.income - Number(form.current_potential_gross_income)) > 1;
  const expensesDiffer = rollUp.hasExpenses && Math.abs(rollUp.expenses - Number(form.current_operating_expenses)) > 1;

  function submit(event: FormEvent) {
    event.preventDefault();
    void saveAndSolve();
  }

  return (
    <form onSubmit={submit} className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="space-y-6">
        {importWarnings.length > 0 && (
          <Banner tone="info" onDismiss={() => setImportWarnings([])}>
            <span className="font-semibold">Import notes.</span> {importWarnings.join(" ")}
          </Banner>
        )}
        <Card
          title="Version details"
          description="Every save is an immutable, numbered version. Record where the numbers came from so the result can be audited later."
          actions={
            <>
              <input
                ref={fileInput}
                type="file"
                accept=".xlsx,.xlsm,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void importFile(file);
                  event.target.value = "";
                }}
              />
              <Button type="button" variant="secondary" size="sm" onClick={() => fileInput.current?.click()} busy={busy === "import"}>
                Import Excel or CSV
              </Button>
              <a href={API_URL + "/v1/imports/underwriting-workbook-template"} className="text-xs font-semibold text-primary-ink underline-offset-2 hover:underline">
                Excel template
              </a>
              <a href={API_URL + "/v1/imports/underwriting-template"} className="text-xs font-semibold text-ink-muted underline-offset-2 hover:underline">
                CSV
              </a>
            </>
          }
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Version label">
              <TextInput required value={meta.label} onChange={(event) => setMeta({ ...meta, label: event.target.value })} />
            </Field>
            <Field label="Source or document reference">
              <TextInput required placeholder="e.g. Broker OM, public record, analyst estimate" value={meta.source} onChange={(event) => setMeta({ ...meta, source: event.target.value })} />
            </Field>
            <Field label="Effective date">
              <TextInput type="date" required value={meta.effective_date} onChange={(event) => setMeta({ ...meta, effective_date: event.target.value })} />
            </Field>
            <Field label="Confidence in these inputs">
              <Select value={meta.confidence_level} onChange={(event) => setMeta({ ...meta, confidence_level: event.target.value as "low" | "medium" | "high" })}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </Select>
            </Field>
          </div>
        </Card>

        <Card
          title="Property"
          description="Descriptive facts that drive per-unit and per-square-foot metrics in the workspace and the exports."
          actions={
            <Button type="button" variant="ghost" size="sm" onClick={() => setShowDetail((current) => !current)}>
              {showDetail ? "Hide rent roll and expenses" : "Rent roll and expenses"}
            </Button>
          }
        >
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Property type">
              <TextInput required value={meta.property_type} onChange={(event) => setMeta({ ...meta, property_type: event.target.value })} />
            </Field>
            <Field label="Class" hint="optional">
              <TextInput value={property.property_class ?? ""} onChange={(event) => setProperty({ property_class: event.target.value || null })} placeholder="A, B or C" />
            </Field>
            <Field
              label="Value bucket"
              hint={
                <button type="button" className="font-semibold text-primary-ink hover:underline" onClick={() => setMeta({ ...meta, value_bucket: valueBucketFor(form.purchase_price) })}>
                  Use {valueBucketFor(form.purchase_price)}
                </button>
              }
            >
              <TextInput required value={meta.value_bucket} onChange={(event) => setMeta({ ...meta, value_bucket: event.target.value })} />
            </Field>
            <Field label="Address" hint="optional">
              <TextInput value={property.address ?? ""} onChange={(event) => setProperty({ address: event.target.value || null })} />
            </Field>
            <NumberField label="Units" hint="optional" suffix="units" min="1" step="1" required={false} value={property.units === null ? "" : String(property.units)} onChange={(value) => setProperty({ units: value === "" ? null : Number(value) })} />
            <NumberField label="Rentable square feet" hint="optional" suffix="SF" min="1" required={false} value={property.rentable_square_feet ?? ""} onChange={(value) => setProperty({ rentable_square_feet: value || null })} />
            <NumberField label="Year built" hint="optional" min="1600" step="1" required={false} value={property.year_built === null ? "" : String(property.year_built)} onChange={(value) => setProperty({ year_built: value === "" ? null : Number(value) })} />
          </div>
          {showDetail && (
            <div className="mt-6 space-y-6 border-t border-line pt-5">
              <LineEditor<RentRollLine>
                title="Rent roll"
                hint={rollUp.units ? `${rollUp.units} units · ${money(rollUp.income)} annual income incl. other income` : "Units × current monthly rent × 12 rolls up to potential gross income."}
                lines={detail.rent_roll}
                onChange={(rent_roll) => setDetail({ ...detail, rent_roll })}
                blank={{ unit_type: "", units: 1, average_square_feet: null, current_monthly_rent: "", market_monthly_rent: null }}
                columns={[
                  { key: "unit_type", label: "Unit type", type: "text", width: "w-40" },
                  { key: "units", label: "Units", type: "number" },
                  { key: "average_square_feet", label: "Avg SF", type: "number" },
                  { key: "current_monthly_rent", label: "Current rent / mo", type: "number" },
                  { key: "market_monthly_rent", label: "Market rent / mo", type: "number" },
                ]}
              />
              <LineEditor<AmountLine>
                title="Other income"
                hint="Annual amounts added to potential gross income."
                lines={detail.other_income}
                onChange={(other_income) => setDetail({ ...detail, other_income })}
                blank={{ category: "", annual_amount: "", note: null }}
                columns={[
                  { key: "category", label: "Category", type: "text", width: "w-48" },
                  { key: "annual_amount", label: "Annual amount", type: "number" },
                  { key: "note", label: "Note", type: "text", width: "flex-1" },
                ]}
              />
              <LineEditor<AmountLine>
                title="Operating expenses"
                hint={rollUp.hasExpenses ? `${money(rollUp.expenses)} total` : "Current-year line items that roll up to operating expenses."}
                lines={detail.operating_expenses}
                onChange={(operating_expenses) => setDetail({ ...detail, operating_expenses })}
                blank={{ category: "", annual_amount: "", note: null }}
                columns={[
                  { key: "category", label: "Category", type: "text", width: "w-48" },
                  { key: "annual_amount", label: "Annual amount", type: "number" },
                  { key: "note", label: "Note", type: "text", width: "flex-1" },
                ]}
              />
              {(incomeDiffers || expensesDiffer) && (
                <div className="flex flex-wrap items-center gap-3 rounded-[var(--radius-control)] border border-warn/30 bg-warn-soft px-4 py-3 text-sm text-warn">
                  <span className="flex-1">
                    {incomeDiffers && `Detail rolls up to ${money(rollUp.income)} of income versus ${money(form.current_potential_gross_income)} entered. `}
                    {expensesDiffer && `Detail rolls up to ${money(rollUp.expenses)} of expenses versus ${money(form.current_operating_expenses)} entered.`}
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      setForm({
                        ...form,
                        ...(incomeDiffers ? { current_potential_gross_income: String(Math.round(rollUp.income)) } : {}),
                        ...(expensesDiffer ? { current_operating_expenses: String(Math.round(rollUp.expenses)) } : {}),
                      })
                    }
                  >
                    Use the roll-up
                  </Button>
                </div>
              )}
              <Field label="Analyst notes" hint="optional">
                <textarea
                  value={detail.notes ?? ""}
                  onChange={(event) => setDetail({ ...detail, notes: event.target.value || null })}
                  rows={3}
                  className="block w-full rounded-[var(--radius-control)] border border-line-strong bg-surface px-3 py-2 text-sm outline-none focus:border-primary focus:ring-4 focus:ring-primary/15"
                  placeholder="Context a reviewer should know: data gaps, broker adjustments, capex expectations…"
                />
              </Field>
              {hasDetail(detail) && (
                <Button type="button" variant="ghost" size="sm" className="text-critical" onClick={() => setDetail(EMPTY_DETAIL)}>
                  Clear property detail
                </Button>
              )}
            </div>
          )}
        </Card>

        <Card title="Acquisition and exit">
          <div className="grid gap-4 sm:grid-cols-2">
            <NumberField label="Reference price" hint="asking or guide" suffix="USD" min="0" value={form.purchase_price} onChange={set("purchase_price")} help="Seeds the solver only. The maximum supportable price is solved from the targets." />
            <NumberField label="Closing costs" suffix="%" min="0" value={rate("closing_cost_rate")} onChange={setRate("closing_cost_rate")} />
            <NumberField label="Exit cap rate" suffix="%" min="0" value={rate("exit_cap_rate")} onChange={setRate("exit_cap_rate")} help="Applied to the year after the hold (forward NOI)." />
            <NumberField label="Selling costs" suffix="%" min="0" value={rate("selling_cost_rate")} onChange={setRate("selling_cost_rate")} />
          </div>
        </Card>

        <Card title="Operations">
          <div className="grid gap-4 sm:grid-cols-2">
            <NumberField
              label="Current potential gross income"
              suffix="USD / yr"
              min="0"
              value={form.current_potential_gross_income}
              onChange={set("current_potential_gross_income")}
              hint={rollUp.hasIncome ? <span className="tabular">detail: {money(rollUp.income)}</span> : undefined}
            />
            <NumberField
              label="Current operating expenses"
              suffix="USD / yr"
              min="0"
              value={form.current_operating_expenses}
              onChange={set("current_operating_expenses")}
              hint={rollUp.hasExpenses ? <span className="tabular">detail: {money(rollUp.expenses)}</span> : undefined}
            />
            <NumberField label="Vacancy and credit loss" suffix="%" min="0" value={rate("vacancy_rate")} onChange={setRate("vacancy_rate")} />
            <NumberField label="Hold period" suffix="years" min="5" step="1" value={form.hold_period_years} onChange={set("hold_period_years")} help="5 to 10 years." />
            <NumberField label="Rent growth" suffix="% / yr" value={rate("rent_growth_rate")} onChange={setRate("rent_growth_rate")} />
            <NumberField label="Expense growth" suffix="% / yr" value={rate("expense_growth_rate")} onChange={setRate("expense_growth_rate")} />
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label="Year 1 convention" help="Going-in cap rate is always Year 1 NOI divided by price, so it matches the first row of the pro forma.">
              <Select value={form.growth_convention} onChange={(event) => setForm({ ...form, growth_convention: event.target.value as DealForm["growth_convention"] })}>
                <option value="current">Year 1 = current figures; growth starts Year 2</option>
                <option value="forward">Entered figures are trailing; grow once before Year 1</option>
              </Select>
            </Field>
            <Field label="Annual rent-growth schedule" hint="optional" help="Percent per growth year, separated by commas. Overrides the flat rate; a short schedule continues its final rate.">
              <TextInput placeholder="e.g. 4, 3, 2, 2, 2" value={form.annual_rent_growth_schedule} onChange={(event) => setForm({ ...form, annual_rent_growth_schedule: event.target.value })} />
            </Field>
          </div>
        </Card>

        <Card title="Financing">
          <div className="grid gap-4 sm:grid-cols-3">
            <NumberField label="Loan-to-value" suffix="%" min="0" value={rate("loan_to_value")} onChange={setRate("loan_to_value")} help="Enter 0 for an all-cash purchase." />
            <NumberField label="Interest rate" suffix="%" min="0" value={rate("annual_interest_rate")} onChange={setRate("annual_interest_rate")} />
            <NumberField label="Amortization" suffix="years" min="1" step="1" value={form.amortization_years} onChange={set("amortization_years")} help="Monthly principal and interest." />
          </div>
        </Card>
      </div>

      <aside className="space-y-4 xl:sticky xl:top-20 xl:self-start">
        <Card tone="panel" title={<span className="text-panel-ink">Investment targets</span>} description="The solver finds the highest price that meets both, and reports which one binds.">
          <div className="space-y-4">
            <PanelNumber label="Target levered IRR" suffix="%" value={toPercentText(form.target_levered_irr)} onChange={(value) => setForm({ ...form, target_levered_irr: fromPercentText(value) })} />
            <PanelNumber label="Minimum DSCR" suffix="x" value={form.minimum_dscr} onChange={(value) => setForm({ ...form, minimum_dscr: value })} />
          </div>
          <Button type="submit" size="lg" className="mt-5 w-full" busy={busy === "solve"}>
            {activeSet && !dirty ? "Re-solve maximum price" : activeSet ? `Save v${activeSet.version + 1} and solve` : "Save v1 and solve"}
          </Button>
          <p className="mt-3 text-xs leading-5 text-panel-muted">
            {activeSet && !dirty ? "Inputs match the active version, so no new version will be created." : "Saving creates a new immutable version; earlier versions stay in History."}
          </p>
        </Card>
        <Card tone="muted">
          <SectionHeading>Quick read</SectionHeading>
          <QuickRead form={form} units={property.units} squareFeet={property.rentable_square_feet} />
        </Card>
        <Card tone="muted">
          <SectionHeading>Conventions</SectionHeading>
          <ul className="space-y-1.5 text-xs leading-5 text-ink-secondary">
            <li>Rates are entered as percentages: 5 means 5%.</li>
            <li>Closing costs are funded with equity, not financed.</li>
            <li>Debt amortizes monthly; the sale repays the remaining balance.</li>
            <li>Cash-on-cash excludes sale proceeds; IRR and multiple include them.</li>
          </ul>
        </Card>
      </aside>
    </form>
  );
}

function PanelNumber({ label, suffix, value, onChange }: { label: string; suffix: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-panel-ink">{label}</span>
      <span className="relative mt-1.5 block">
        <input
          type="number"
          step="any"
          min="0"
          required
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="tabular h-11 w-full rounded-[var(--radius-control)] border border-panel-line bg-panel-soft px-3 pr-10 text-base text-panel-ink outline-none focus:border-panel-accent"
        />
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-panel-muted">{suffix}</span>
      </span>
    </label>
  );
}

/** Live arithmetic on the entered inputs so an analyst sees the going-in picture before solving. */
function QuickRead({ form, units, squareFeet }: { form: DealForm; units: number | null; squareFeet: string | null }) {
  const pgi = Number(form.current_potential_gross_income);
  const egi = pgi * (1 - Number(form.vacancy_rate));
  const noi = egi - Number(form.current_operating_expenses);
  const price = Number(form.purchase_price);
  const loan = price * Number(form.loan_to_value);
  const rate = Number(form.annual_interest_rate) / 12;
  const n = Number(form.amortization_years) * 12;
  const payment = loan > 0 ? (rate === 0 ? loan / n : (loan * rate) / (1 - Math.pow(1 + rate, -n))) * 12 : 0;
  const rows: Array<[string, string]> = [
    ["Current NOI", money(noi)],
    ["Going-in cap at reference price", price > 0 ? percent(noi / price) : "—"],
    ["Expense ratio (OpEx / EGI)", egi > 0 ? percent(Number(form.current_operating_expenses) / egi) : "—"],
    ["Annual debt service at reference", loan > 0 ? money(payment) : "all-cash"],
    ["Year 1 DSCR at reference", payment > 0 ? (noi / payment).toFixed(2) + "x" : "—"],
  ];
  if (units) rows.push(["Reference price per unit", money(price / units)]);
  if (squareFeet && Number(squareFeet) > 0) rows.push(["Reference price per SF", "$" + (price / Number(squareFeet)).toFixed(2)]);
  return (
    <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1.5 text-xs">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-ink-muted">{label}</dt>
          <dd className="tabular text-right font-medium text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

type Column<T> = { key: keyof T & string; label: string; type: "text" | "number"; width?: string };

function LineEditor<T extends Record<string, string | number | null>>({
  title,
  hint,
  lines,
  onChange,
  blank,
  columns,
}: {
  title: string;
  hint?: string;
  lines: T[];
  onChange: (lines: T[]) => void;
  blank: T;
  columns: Column<T>[];
}) {
  const update = (index: number, key: keyof T, value: string) => {
    const next = lines.map((line, i) => (i === index ? { ...line, [key]: value === "" ? (typeof blank[key] === "number" ? 0 : null) : typeof blank[key] === "number" ? Number(value) : value } : line));
    onChange(next);
  };
  return (
    <div>
      <SectionHeading hint={hint}>{title}</SectionHeading>
      {lines.length > 0 && (
        <div className="mb-2 hidden gap-2 text-[11px] font-semibold uppercase tracking-wide text-ink-muted sm:flex">
          {columns.map((column) => (
            <span key={column.key} className={column.width ?? "w-32"}>
              {column.label}
            </span>
          ))}
        </div>
      )}
      <div className="space-y-2">
        {lines.map((line, index) => (
          <div key={index} className="flex flex-wrap items-center gap-2">
            {columns.map((column) => (
              <input
                key={column.key}
                type={column.type}
                step="any"
                aria-label={column.label}
                placeholder={column.label}
                value={line[column.key] === null || line[column.key] === undefined ? "" : String(line[column.key])}
                onChange={(event) => update(index, column.key, event.target.value)}
                className={
                  (column.width ?? "w-32") +
                  " tabular h-9 rounded-[var(--radius-control)] border border-line-strong bg-surface px-2.5 text-sm outline-none focus:border-primary focus:ring-4 focus:ring-primary/15"
                }
              />
            ))}
            <button type="button" aria-label="Remove line" onClick={() => onChange(lines.filter((_, i) => i !== index))} className="h-9 w-9 rounded-[var(--radius-control)] text-ink-muted hover:bg-surface-muted hover:text-critical">
              ×
            </button>
          </div>
        ))}
      </div>
      <div className="mt-2 flex items-center gap-3">
        <Button type="button" variant="ghost" size="sm" onClick={() => onChange([...lines, { ...blank }])}>
          + Add line
        </Button>
        {lines.length > 0 && <Badge tone="neutral">{lines.length} lines</Badge>}
      </div>
    </div>
  );
}
