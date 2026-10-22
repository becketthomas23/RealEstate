"use client";

import { useState } from "react";
import { constraintLabel, money, multiple, percent, percent2 } from "@/lib/format";
import { SENSITIVITY_LABELS, type SensitivityKey } from "@/lib/types";
import { CashFlowChart } from "../charts";
import { Badge, Button, Card, EmptyState, KeyValue, SectionHeading, Select, Stat, severityTone } from "../ui";
import type { Workspace } from "./useDealWorkspace";

const DRIVERS = Object.keys(SENSITIVITY_LABELS) as SensitivityKey[];

export function PricingTab({ workspace, onGoToInputs }: { workspace: Workspace; onGoToInputs: () => void }) {
  const { result, form, sensitivity, grid, busy, runSensitivity, runGrid, activeSet } = workspace;
  const [gridX, setGridX] = useState<SensitivityKey>("rent_growth_rate");
  const [gridY, setGridY] = useState<SensitivityKey>("exit_cap_rate");

  if (!result) {
    return (
      <EmptyState
        title="No solved price yet"
        description="Enter the deal assumptions and investment targets, then save and solve. The maximum supportable price and every downstream analysis will appear here."
        action={<Button onClick={onGoToInputs}>Go to inputs</Button>}
      />
    );
  }

  const uw = result.underwriting;
  const years = uw.operating_projection.map((year) => year.year);
  const recurring = uw.annual_operating_cash_flows.map(Number);
  const exitProceeds = Number(uw.disposition.net_sale_proceeds_to_equity);
  const target = Number(form.target_levered_irr);
  const loanAmount = uw.loan_amount ?? String(Number(result.maximum_purchase_price) * Number(form.loan_to_value));
  const equity = uw.initial_equity ?? String(Number(result.maximum_purchase_price) * (1 + Number(form.closing_cost_rate)) - Number(loanAmount));

  return (
    <div className="space-y-6">
      <Card tone="panel" className="rise">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-panel-accent">Maximum supportable price</p>
            <p className="tabular mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">{money(result.maximum_purchase_price)}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
              <Badge tone="on-panel">Bound by {constraintLabel(result.binding_constraint)}</Badge>
              <Badge tone="on-panel">{result.iterations} solver steps</Badge>
              {activeSet && <Badge tone="on-panel">v{activeSet.version}</Badge>}
            </div>
            <div className="mt-6 rounded-xl border border-panel-line bg-panel-soft p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-panel-muted">Recommended bid range</p>
              <p className="tabular mt-1 text-lg font-semibold text-panel-accent">
                {money(result.recommended_bid_floor)} <span className="text-panel-muted">to</span> {money(result.recommended_bid_ceiling)}
              </p>
              <p className="mt-1 text-xs text-panel-muted">A 5% negotiation buffer below the maximum. The ceiling is the maximum itself.</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-5 sm:grid-cols-3">
            <Stat onPanel tone="accent" label="Levered IRR" value={percent(uw.returns.levered_irr)} hint={"target " + percent(target)} />
            <Stat onPanel label="Equity multiple" value={multiple(uw.returns.equity_multiple)} />
            <Stat onPanel label="Min DSCR" value={uw.returns.minimum_dscr === null ? "N/A" : multiple(uw.returns.minimum_dscr)} hint={uw.returns.minimum_dscr === null ? "all-cash" : "floor " + multiple(form.minimum_dscr)} />
            <Stat onPanel label="Going-in cap" value={percent2(uw.going_in_cap_rate)} hint="Year 1 NOI / price" />
            <Stat onPanel label="Debt yield" value={uw.debt_yield === null ? "N/A" : percent2(uw.debt_yield)} />
            <Stat onPanel label="Equity required" value={money(equity)} hint={"loan " + money(loanAmount)} />
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Card title="Equity cash flow" description="Recurring cash flow after debt service by year; the final year adds net exit proceeds.">
          <CashFlowChart years={years} recurring={recurring} exit={exitProceeds} />
          <div className="-mx-5 mt-4 overflow-x-auto sm:-mx-6">
            <table className="data-table min-w-[620px]">
              <thead>
                <tr>
                  <th>Year</th>
                  <th>NOI</th>
                  <th>Debt service</th>
                  <th>Recurring CF</th>
                  <th>Cash-on-cash</th>
                  <th>DSCR</th>
                  <th>Total CF</th>
                </tr>
              </thead>
              <tbody>
                {uw.operating_projection.map((year, index) => {
                  const isExit = index === years.length - 1;
                  return (
                    <tr key={year.year}>
                      <td className="font-medium">
                        {year.year} {isExit && <Badge tone="primary" className="ml-1">Exit</Badge>}
                      </td>
                      <td>{money(year.net_operating_income)}</td>
                      <td className="text-ink-secondary">{money(uw.debt_projection[index].debt_service)}</td>
                      <td className="font-semibold text-primary-ink">{money(uw.annual_operating_cash_flows[index])}</td>
                      <td>{percent(uw.returns.cash_on_cash_by_year[index])}</td>
                      <td>{uw.returns.dscr_by_year?.[index] ? multiple(uw.returns.dscr_by_year[index]) : "N/A"}</td>
                      <td className="font-medium">{money(uw.annual_cash_flows[index])}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="space-y-6">
          <Card title="Risk flags" description="Rules-based checks at the solved price, each with its threshold.">
            {uw.risk_flags.length === 0 ? (
              <p className="rounded-[var(--radius-control)] border border-good/30 bg-good-soft px-3 py-2 text-sm text-primary-ink">No rules-based risk flags triggered.</p>
            ) : (
              <ul className="space-y-2">
                {uw.risk_flags.map((flag) => (
                  <li key={flag.code} className="flex gap-3 rounded-[var(--radius-control)] border border-line p-3 text-sm">
                    <Badge tone={severityTone(flag.severity)} className="h-fit">
                      {flag.severity}
                    </Badge>
                    <div className="min-w-0">
                      <p className="leading-5 text-ink">{flag.message}</p>
                      <p className="tabular mt-1 text-xs text-ink-muted">
                        observed {formatFlagValue(flag.code, flag.observed_value)} · threshold {formatFlagValue(flag.code, flag.threshold)}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Exit and sources">
            <KeyValue
              rows={[
                ["Terminal NOI (year after hold)", money(uw.terminal_noi)],
                ["Gross sale price", money(uw.disposition.gross_sale_price)],
                ["Selling costs", money(uw.disposition.selling_costs)],
                ["Loan payoff", money(uw.disposition.loan_payoff)],
                ["Net sale proceeds to equity", money(uw.disposition.net_sale_proceeds_to_equity)],
                ["Closing costs", money(uw.closing_costs ?? Number(result.maximum_purchase_price) * Number(form.closing_cost_rate))],
                ["Total equity distributed", money(uw.returns.total_equity_distributed)],
              ]}
            />
          </Card>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="One-way price sensitivity"
          description="Each case changes one assumption and re-solves the maximum price with the same targets."
          actions={
            <Button size="sm" variant="secondary" onClick={() => void runSensitivity()} busy={busy === "sensitivity"}>
              {sensitivity ? "Re-run" : "Run"}
            </Button>
          }
        >
          {!sensitivity ? (
            <EmptyState compact title="Not run for this version" description="Rent growth and interest rate move ±100 bps, exit cap ±50 bps." />
          ) : (
            <div className="space-y-5">
              {sensitivity.dimensions.map((dimension) => {
                const base = dimension.points.find((point) => point.label.startsWith("Base"))?.maximum_purchase_price;
                return (
                  <div key={dimension.key}>
                    <SectionHeading hint={dimension.key === "exit_cap_rate" ? "±50 bps" : "±100 bps"}>{dimension.label}</SectionHeading>
                    {dimension.description && <p className="mb-2 text-xs text-ink-muted">{dimension.description}</p>}
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Case</th>
                          <th>Input</th>
                          <th>Max price</th>
                          <th>vs base</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dimension.points.map((point) => {
                          const delta = point.maximum_purchase_price && base ? Number(point.maximum_purchase_price) - Number(base) : null;
                          return (
                            <tr key={point.label}>
                              <td className="font-medium">{point.label}</td>
                              <td className="text-ink-secondary">{point.value === null ? "Scheduled" : percent(point.value)}</td>
                              <td className="font-semibold text-primary-ink" title={point.error ?? undefined}>
                                {point.maximum_purchase_price ? money(point.maximum_purchase_price) : "Unavailable"}
                              </td>
                              <td className={delta === null || delta === 0 ? "text-ink-muted" : delta > 0 ? "text-good" : "text-critical"}>
                                {delta === null ? "—" : delta === 0 ? "base" : (delta > 0 ? "+" : "−") + money(Math.abs(delta))}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card
          title="Two-way IRR grid"
          description={"Levered IRR at the solved price (" + money(result.maximum_purchase_price) + "). The centre cell should match the target."}
          actions={
            <Button size="sm" variant="secondary" onClick={() => void runGrid(gridX, gridY)} busy={busy === "grid"}>
              {grid ? "Re-run" : "Run"}
            </Button>
          }
        >
          <div className="mb-4 grid grid-cols-2 gap-3">
            <label className="text-xs font-semibold text-ink-secondary">
              Rows
              <Select value={gridX} onChange={(event) => setGridX(event.target.value as SensitivityKey)} className="mt-1">
                {DRIVERS.map((key) => (
                  <option key={key} value={key}>
                    {SENSITIVITY_LABELS[key]}
                  </option>
                ))}
              </Select>
            </label>
            <label className="text-xs font-semibold text-ink-secondary">
              Columns
              <Select value={gridY} onChange={(event) => setGridY(event.target.value as SensitivityKey)} className="mt-1">
                {DRIVERS.map((key) => (
                  <option key={key} value={key}>
                    {SENSITIVITY_LABELS[key]}
                  </option>
                ))}
              </Select>
            </label>
          </div>
          {!grid ? (
            <EmptyState compact title="Not run" description="Choose two drivers and run to see how the IRR moves when both change." />
          ) : (
            <GridTable grid={grid} target={target} />
          )}
        </Card>
      </div>
    </div>
  );
}

function GridTable({ grid, target }: { grid: NonNullable<Workspace["grid"]>; target: number }) {
  const rows = Array.from(new Set(grid.result.scenarios.map((s) => s.values[grid.x])));
  const cols = Array.from(new Set(grid.result.scenarios.map((s) => s.values[grid.y])));
  const lookup = new Map(grid.result.scenarios.map((s) => [s.values[grid.x] + "|" + s.values[grid.y], s.metric_value]));
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>
            {SENSITIVITY_LABELS[grid.x]} ↓ / {SENSITIVITY_LABELS[grid.y]} →
          </th>
          {cols.map((col) => (
            <th key={col}>{percent2(col)}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, rowIndex) => (
          <tr key={row}>
            <td className="font-medium">{percent2(row)}</td>
            {cols.map((col, colIndex) => {
              const value = lookup.get(row + "|" + col);
              const isBase = rowIndex === Math.floor(rows.length / 2) && colIndex === Math.floor(cols.length / 2);
              const meets = value !== null && value !== undefined && Number(value) >= target;
              return (
                <td key={col} className={(isBase ? "bg-primary-soft font-semibold " : "") + (value === null || value === undefined ? "text-ink-muted" : meets ? "text-primary-ink" : "text-critical")}>
                  {value === null || value === undefined ? "—" : percent(value)}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function formatFlagValue(code: string, value: string) {
  if (code.includes("dscr")) return multiple(value);
  if (code === "negative_equity_cash_flow") return money(value);
  return percent2(value);
}
