"use client";

import { FormEvent, useRef } from "react";
import { API_URL } from "@/lib/api";
import { fromPercentText, toPercentText, valueBucketFor } from "@/lib/format";
import type { DealForm } from "@/lib/types";
import { Button, Card, Field, NumberField, SectionHeading, Select, TextInput } from "../ui";
import type { Workspace } from "./useDealWorkspace";

type RateKey = Extract<
  keyof DealForm,
  | "closing_cost_rate"
  | "loan_to_value"
  | "annual_interest_rate"
  | "exit_cap_rate"
  | "selling_cost_rate"
  | "vacancy_rate"
  | "rent_growth_rate"
  | "expense_growth_rate"
  | "target_levered_irr"
>;

export function InputsTab({ workspace }: { workspace: Workspace }) {
  const { form, setForm, meta, setMeta, activeSet, busy, saveAndSolve, importCsv, dirty } = workspace;
  const fileInput = useRef<HTMLInputElement>(null);
  const set = (key: keyof DealForm) => (value: string) => setForm({ ...form, [key]: value });
  const setRate = (key: RateKey) => (value: string) => setForm({ ...form, [key]: fromPercentText(value) });
  const rate = (key: RateKey) => toPercentText(form[key]);

  function submit(event: FormEvent) {
    event.preventDefault();
    void saveAndSolve();
  }

  return (
    <form onSubmit={submit} className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="space-y-6">
        <Card
          title="Version details"
          description="Every save is an immutable, numbered version. Record where the numbers came from so the result can be audited later."
          actions={
            <>
              <input ref={fileInput} type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void importCsv(file);
                event.target.value = "";
              }} />
              <Button type="button" variant="secondary" size="sm" onClick={() => fileInput.current?.click()} busy={busy === "import"}>
                Import CSV
              </Button>
              <a href={API_URL + "/v1/imports/underwriting-template"} className="text-xs font-semibold text-primary-ink underline-offset-2 hover:underline">
                Template
              </a>
            </>
          }
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Version label">
              <TextInput required value={meta.label} onChange={(event) => setMeta({ ...meta, label: event.target.value })} />
            </Field>
            <Field label="Source or document reference">
              <TextInput
                required
                placeholder="e.g. Broker OM, public record, analyst estimate"
                value={meta.source}
                onChange={(event) => setMeta({ ...meta, source: event.target.value })}
              />
            </Field>
            <Field label="Effective date">
              <TextInput type="date" required value={meta.effective_date} onChange={(event) => setMeta({ ...meta, effective_date: event.target.value })} />
            </Field>
            <Field label="Confidence in these inputs">
              <Select value={meta.confidence_level} onChange={(event) => setMeta({ ...meta, confidence_level: event.target.value as DealForm extends never ? never : "low" | "medium" | "high" })}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </Select>
            </Field>
            <Field label="Property type">
              <TextInput required value={meta.property_type} onChange={(event) => setMeta({ ...meta, property_type: event.target.value })} />
            </Field>
            <Field
              label="Asset value bucket"
              hint={
                <button type="button" className="font-semibold text-primary-ink hover:underline" onClick={() => setMeta({ ...meta, value_bucket: valueBucketFor(form.purchase_price) })}>
                  Use {valueBucketFor(form.purchase_price)}
                </button>
              }
              help="A calibration segment for market history, not an appraisal."
            >
              <TextInput required value={meta.value_bucket} onChange={(event) => setMeta({ ...meta, value_bucket: event.target.value })} />
            </Field>
          </div>
        </Card>

        <Card title="Acquisition and exit">
          <div className="grid gap-4 sm:grid-cols-2">
            <NumberField
              label="Reference price"
              hint="asking or guide"
              suffix="USD"
              min="0"
              value={form.purchase_price}
              onChange={set("purchase_price")}
              help="Seeds the solver only. The maximum supportable price is solved from the targets below."
            />
            <NumberField label="Closing costs" suffix="%" min="0" value={rate("closing_cost_rate")} onChange={setRate("closing_cost_rate")} />
            <NumberField label="Exit cap rate" suffix="%" min="0" value={rate("exit_cap_rate")} onChange={setRate("exit_cap_rate")} help="Applied to the year after the hold (forward NOI)." />
            <NumberField label="Selling costs" suffix="%" min="0" value={rate("selling_cost_rate")} onChange={setRate("selling_cost_rate")} />
          </div>
        </Card>

        <Card title="Operations">
          <div className="grid gap-4 sm:grid-cols-2">
            <NumberField label="Current potential gross income" suffix="USD / yr" min="0" value={form.current_potential_gross_income} onChange={set("current_potential_gross_income")} />
            <NumberField label="Current operating expenses" suffix="USD / yr" min="0" value={form.current_operating_expenses} onChange={set("current_operating_expenses")} />
            <NumberField label="Vacancy and credit loss" suffix="%" min="0" value={rate("vacancy_rate")} onChange={setRate("vacancy_rate")} />
            <NumberField label="Hold period" suffix="years" min="5" step="1" value={form.hold_period_years} onChange={set("hold_period_years")} help="5 to 10 years." />
            <NumberField label="Rent growth" suffix="% / yr" value={rate("rent_growth_rate")} onChange={setRate("rent_growth_rate")} />
            <NumberField label="Expense growth" suffix="% / yr" value={rate("expense_growth_rate")} onChange={setRate("expense_growth_rate")} />
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field
              label="Year 1 convention"
              help="Going-in cap rate is always Year 1 NOI divided by price, so it matches the first row of the pro forma."
            >
              <Select value={form.growth_convention} onChange={(event) => setForm({ ...form, growth_convention: event.target.value as DealForm["growth_convention"] })}>
                <option value="current">Year 1 = current figures; growth starts Year 2</option>
                <option value="forward">Entered figures are trailing; grow once before Year 1</option>
              </Select>
            </Field>
            <Field
              label="Annual rent-growth schedule"
              hint="optional"
              help="Percent per growth year, separated by commas. Overrides the flat rate; a short schedule continues its final rate."
            >
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
            <label className="block">
              <span className="text-sm font-medium text-panel-ink">Target levered IRR</span>
              <span className="relative mt-1.5 block">
                <input
                  type="number"
                  step="any"
                  min="0"
                  required
                  value={toPercentText(form.target_levered_irr)}
                  onChange={(event) => setForm({ ...form, target_levered_irr: fromPercentText(event.target.value) })}
                  className="tabular h-11 w-full rounded-[var(--radius-control)] border border-panel-line bg-panel-soft px-3 pr-10 text-base text-panel-ink outline-none focus:border-panel-accent"
                />
                <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-panel-muted">%</span>
              </span>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-panel-ink">Minimum DSCR</span>
              <span className="relative mt-1.5 block">
                <input
                  type="number"
                  step="any"
                  min="0"
                  required
                  value={form.minimum_dscr}
                  onChange={(event) => setForm({ ...form, minimum_dscr: event.target.value })}
                  className="tabular h-11 w-full rounded-[var(--radius-control)] border border-panel-line bg-panel-soft px-3 pr-10 text-base text-panel-ink outline-none focus:border-panel-accent"
                />
                <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-panel-muted">x</span>
              </span>
            </label>
          </div>
          <Button type="submit" size="lg" className="mt-5 w-full" busy={busy === "solve"}>
            {activeSet && !dirty ? "Re-solve maximum price" : activeSet ? `Save v${activeSet.version + 1} and solve` : "Save v1 and solve"}
          </Button>
          <p className="mt-3 text-xs leading-5 text-panel-muted">
            {activeSet && !dirty
              ? "Inputs match the active version, so no new version will be created."
              : "Saving creates a new immutable version; earlier versions stay in History."}
          </p>
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
