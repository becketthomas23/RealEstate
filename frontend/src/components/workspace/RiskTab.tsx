"use client";

import { useState } from "react";
import { API_URL } from "@/lib/api";
import { money, multiple, percent, percent2, signedMoney, signedPercent, today, titleCase, valueBucketFor } from "@/lib/format";
import { SENSITIVITY_LABELS, type Distribution, type SensitivityKey, type SimulationSummary } from "@/lib/types";
import { Histogram, RangeBar, Tornado } from "../charts";
import { Badge, Banner, Button, Card, EmptyState, Field, NumberField, SectionHeading, Select, Stat, TextInput } from "../ui";
import type { Workspace } from "./useDealWorkspace";

const DRIVERS = Object.keys(SENSITIVITY_LABELS) as SensitivityKey[];

export function RiskTab({ workspace, onGoToInputs }: { workspace: Workspace; onGoToInputs: () => void }) {
  const { result, form, meta, simulation, simulationPrice, calibration, busy, runSimulation, previewCalibration } = workspace;
  const [drivers, setDrivers] = useState<SensitivityKey[]>(["rent_growth_rate", "exit_cap_rate", "vacancy_rate"]);
  const [confidence, setConfidence] = useState<"low" | "medium" | "high">("medium");
  const [distribution, setDistribution] = useState<Distribution>("triangular");
  const [iterations, setIterations] = useState("2000");
  const [file, setFile] = useState<File | null>(null);
  const [propertyType, setPropertyType] = useState(meta.property_type);
  const [valueBucket, setValueBucket] = useState(meta.value_bucket);
  const [source, setSource] = useState("User-provided aggregate market history");
  const [asOfDate, setAsOfDate] = useState(today());

  if (!result) {
    return <EmptyState title="Solve a price first" description="The risk simulation samples the deal at the solved maximum price, so it needs a solved version." action={<Button onClick={onGoToInputs}>Go to inputs</Button>} />;
  }

  const toggle = (key: SensitivityKey) => setDrivers((current) => (current.includes(key) ? current.filter((item) => item !== key) : [...current, key]));
  const target = Number(form.target_levered_irr);
  const floor = Number(form.minimum_dscr);
  const stale = simulation && simulationPrice && simulationPrice !== result.maximum_purchase_price;
  const meets = simulation?.levered_irr.probability_meeting_target ? Number(simulation.levered_irr.probability_meeting_target) : null;

  return (
    <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
      <div className="space-y-6">
        <Card title="Simulation setup" description={"Seeded, correlated Monte Carlo at the solved price (" + money(result.maximum_purchase_price) + ")."}>
          <SectionHeading>Risk drivers</SectionHeading>
          <div className="grid grid-cols-2 gap-2">
            {DRIVERS.map((key) => (
              <label key={key} className="flex items-center gap-2 rounded-[var(--radius-control)] border border-line px-3 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary-soft">
                <input type="checkbox" checked={drivers.includes(key)} onChange={() => toggle(key)} className="accent-primary" />
                {SENSITIVITY_LABELS[key]}
              </label>
            ))}
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <Field label="Distribution" help="Shape of each driver inside its band.">
              <Select value={distribution} onChange={(event) => setDistribution(event.target.value as Distribution)}>
                <option value="triangular">Triangular (peaks at base)</option>
                <option value="normal">Truncated normal</option>
                <option value="uniform">Uniform</option>
              </Select>
            </Field>
            <Field label="Confidence" help="Band width: low is widest.">
              <Select value={confidence} onChange={(event) => setConfidence(event.target.value as typeof confidence)}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </Select>
            </Field>
            <NumberField label="Iterations" min="100" step="100" value={iterations} onChange={setIterations} help="100 to 10,000. Seed 42 keeps runs reproducible." />
          </div>
          <Button className="mt-5 w-full" onClick={() => void runSimulation({ drivers, confidence, distribution, iterations: Number(iterations) })} busy={busy === "simulation"} disabled={!drivers.length}>
            {simulation ? "Re-run simulation" : "Run simulation"}
          </Button>
          <p className="mt-3 text-xs leading-5 text-ink-muted">
            Target IRR {percent(target)} and DSCR floor {floor.toFixed(2)}x come from the Inputs tab. Results are saved with the version and can be included in the Excel export.
          </p>
        </Card>

        <Card
          title="Market calibration"
          description="Optional. Upload aggregate quarterly history to let drivers move together and to size their bands from the historical P10 to P90."
          actions={
            <a href={API_URL + "/v1/market-calibrations/template"} className="text-xs font-semibold text-primary-ink underline-offset-2 hover:underline">
              CSV template
            </a>
          }
        >
          <div className="grid gap-3">
            <Field label="Property type">
              <TextInput value={propertyType} onChange={(event) => setPropertyType(event.target.value)} />
            </Field>
            <Field
              label="Value bucket"
              hint={
                <button type="button" className="font-semibold text-primary-ink hover:underline" onClick={() => setValueBucket(valueBucketFor(result.maximum_purchase_price))}>
                  Use {valueBucketFor(result.maximum_purchase_price)}
                </button>
              }
            >
              <TextInput value={valueBucket} onChange={(event) => setValueBucket(event.target.value)} />
            </Field>
            <Field label="Source or publisher">
              <TextInput value={source} onChange={(event) => setSource(event.target.value)} />
            </Field>
            <Field label="Source as-of or pull date">
              <TextInput type="date" value={asOfDate} onChange={(event) => setAsOfDate(event.target.value)} />
            </Field>
            <Field label="Aggregate history CSV">
              <input type="file" accept=".csv,text/csv" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="block w-full text-xs text-ink-secondary file:mr-3 file:rounded-md file:border-0 file:bg-surface-muted file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-ink" />
            </Field>
          </div>
          <Button variant="secondary" className="mt-4 w-full" disabled={!file || !source.trim() || !asOfDate} busy={busy === "calibration"} onClick={() => file && void previewCalibration({ file, propertyType, valueBucket, source, asOfDate })}>
            Load correlations
          </Button>
          {calibration && (
            <div className="mt-4 rounded-[var(--radius-control)] border border-primary/20 bg-primary-soft p-3 text-xs text-primary-ink">
              <p className="font-semibold">
                {calibration.context.property_type} · {calibration.context.value_bucket}
              </p>
              <p className="mt-1">
                {calibration.context.observations} periods, {calibration.context.period_start} to {calibration.context.period_end}. Source: {calibration.context.source} (as of {calibration.context.source_as_of_date}).
              </p>
              <ul className="mt-2 space-y-1">
                {calibration.driver_ranges
                  .filter((item) => drivers.includes(item.key))
                  .map((item) => (
                    <li key={item.key} className="tabular">
                      <span className="font-semibold">{SENSITIVITY_LABELS[item.key]}</span> P10 {percent(item.percentile_10)} · P50 {percent(item.percentile_50)} · P90 {percent(item.percentile_90)}
                    </li>
                  ))}
              </ul>
              {calibration.correlations.filter((item) => drivers.includes(item.first_key) && drivers.includes(item.second_key)).length > 0 && (
                <ul className="mt-2 space-y-1 border-t border-primary/15 pt-2">
                  {calibration.correlations
                    .filter((item) => drivers.includes(item.first_key) && drivers.includes(item.second_key))
                    .map((item) => (
                      <li key={item.first_key + item.second_key} className="tabular">
                        {SENSITIVITY_LABELS[item.first_key]} / {SENSITIVITY_LABELS[item.second_key]}: <strong>{Number(item.coefficient).toFixed(2)}</strong>
                      </li>
                    ))}
                </ul>
              )}
              {calibration.warnings.map((warning) => (
                <p key={warning} className="mt-2 rounded-md bg-warn-soft px-2 py-1 text-warn">
                  {warning}
                </p>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="space-y-6">
        {!simulation ? (
          <EmptyState title="No simulation for this version" description="Pick the drivers to vary and run the simulation. Results are saved with the version and the price they describe." />
        ) : (
          <>
            {stale && (
              <Banner tone="info">
                This simulation describes a price of {money(simulationPrice)}; the current solved price is {money(result.maximum_purchase_price)}. Re-run to update it.
              </Banner>
            )}
            <Card title="Headline risk" description={`${simulation.iterations.toLocaleString()} cases at ${money(simulationPrice ?? result.maximum_purchase_price)} · base case IRR ${percent(simulation.base_case_irr ?? result.underwriting.returns.levered_irr)}.`}>
              <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-5">
                <Stat label="Median IRR" value={percent(simulation.levered_irr.percentile_50)} hint={"P10 " + percent(simulation.levered_irr.percentile_10) + " · P90 " + percent(simulation.levered_irr.percentile_90)} tone="accent" />
                <Stat label="Meets target" value={meets === null ? "—" : percent(meets)} hint={"at or above " + percent(target)} tone={meets === null ? "default" : meets >= 0.5 ? "good" : "warn"} />
                <Stat label="Probability of loss" value={simulation.probability_of_loss ? percent(simulation.probability_of_loss) : "—"} hint="IRR below 0%" tone={Number(simulation.probability_of_loss ?? 0) > 0.05 ? "critical" : "default"} />
                <Stat
                  label="DSCR below floor"
                  value={simulation.probability_dscr_below_floor === null || simulation.probability_dscr_below_floor === undefined ? "N/A" : percent(simulation.probability_dscr_below_floor)}
                  hint={"floor " + floor.toFixed(2) + "x"}
                  tone={Number(simulation.probability_dscr_below_floor ?? 0) > 0.1 ? "warn" : "default"}
                />
                <Stat label="Negative cash-flow year" value={simulation.probability_negative_cash_flow_year ? percent(simulation.probability_negative_cash_flow_year) : "—"} hint="any year after debt service" />
              </div>
            </Card>

            <Card title="Levered IRR distribution" description="Each bar is a band of outcomes; the dashed line is the target and the solid line the base case.">
              {simulation.irr_histogram ? (
                <Histogram
                  bins={simulation.irr_histogram.map((bin) => ({ lower: Number(bin.lower), upper: Number(bin.upper), count: bin.count }))}
                  target={target}
                  base={simulation.base_case_irr ? Number(simulation.base_case_irr) : null}
                />
              ) : (
                <RangeBar
                  low={Number(simulation.levered_irr.percentile_10)}
                  median={Number(simulation.levered_irr.percentile_50)}
                  high={Number(simulation.levered_irr.percentile_90)}
                  target={target}
                  minimum={Math.min(Number(simulation.levered_irr.minimum), target) - 0.01}
                  maximum={Math.max(Number(simulation.levered_irr.maximum), target) + 0.01}
                />
              )}
              <div className="-mx-5 mt-5 overflow-x-auto sm:-mx-6">
                <table className="data-table min-w-[760px]">
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Min</th>
                      <th>P5</th>
                      <th>P10</th>
                      <th>P25</th>
                      <th>Median</th>
                      <th>P75</th>
                      <th>P90</th>
                      <th>P95</th>
                      <th>Max</th>
                      <th>Std dev</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(
                      [
                        ["Levered IRR", simulation.levered_irr, percent],
                        ["Equity multiple", simulation.equity_multiple, multiple],
                        ["Minimum DSCR", simulation.minimum_dscr ?? null, multiple],
                        ["Year 1 cash-on-cash", simulation.year_one_cash_on_cash ?? null, percent],
                        ["Terminal NOI", simulation.terminal_noi, money],
                        ["Net sale proceeds", simulation.net_sale_proceeds, money],
                      ] as Array<[string, SimulationSummary | null, (value: string) => string]>
                    )
                      .filter((row): row is [string, SimulationSummary, (value: string) => string] => row[1] !== null)
                      .map(([label, summary, fmt]) => (
                        <tr key={label}>
                          <td className="font-medium">{label}</td>
                          <td>{fmt(summary.minimum)}</td>
                          <td>{summary.percentile_5 ? fmt(summary.percentile_5) : "—"}</td>
                          <td>{fmt(summary.percentile_10)}</td>
                          <td>{summary.percentile_25 ? fmt(summary.percentile_25) : "—"}</td>
                          <td className="font-semibold">{fmt(summary.percentile_50)}</td>
                          <td>{summary.percentile_75 ? fmt(summary.percentile_75) : "—"}</td>
                          <td>{fmt(summary.percentile_90)}</td>
                          <td>{summary.percentile_95 ? fmt(summary.percentile_95) : "—"}</td>
                          <td>{fmt(summary.maximum)}</td>
                          <td className="text-ink-muted">{summary.standard_deviation ? fmt(summary.standard_deviation) : "—"}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </Card>

            {simulation.driver_impacts && simulation.driver_impacts.some((item) => item.irr_at_low && item.irr_at_high) && (
              <Card title="What moves the return" description="Each driver is moved to its own P10 and P90 draw with every other input held at base. Longer bars matter more.">
                <Tornado
                  base={Number(simulation.base_case_irr ?? result.underwriting.returns.levered_irr)}
                  items={simulation.driver_impacts
                    .filter((item) => item.irr_at_low && item.irr_at_high)
                    .map((item) => ({
                      label: SENSITIVITY_LABELS[item.key],
                      low: Number(item.irr_at_low),
                      high: Number(item.irr_at_high),
                      lowInput: percent2(item.sampled_low ?? "0"),
                      highInput: percent2(item.sampled_high ?? "0"),
                    }))}
                />
                <div className="-mx-5 mt-4 overflow-x-auto sm:-mx-6">
                  <table className="data-table min-w-[640px]">
                    <thead>
                      <tr>
                        <th>Driver</th>
                        <th>Share of IRR variance</th>
                        <th>IRR per +100 bps</th>
                        <th>Recurring CF per +100 bps</th>
                        <th>Sampled P10 to P90</th>
                      </tr>
                    </thead>
                    <tbody>
                      {simulation.driver_impacts.map((item) => (
                        <tr key={item.key}>
                          <td className="font-medium">{SENSITIVITY_LABELS[item.key]}</td>
                          <td>
                            {percent(item.relative_influence)} <Badge tone={Number(item.return_correlation) >= 0 ? "good" : "warn"}>{Number(item.return_correlation) >= 0 ? "with IRR" : "against IRR"}</Badge>
                          </td>
                          <td className={Number(item.irr_change_per_100_bps) >= 0 ? "text-good" : "text-critical"}>{signedPercent(item.irr_change_per_100_bps)}</td>
                          <td className={Number(item.cash_flow_change_per_100_bps) >= 0 ? "text-good" : "text-critical"}>{signedMoney(item.cash_flow_change_per_100_bps)}</td>
                          <td className="text-ink-secondary">{item.sampled_low && item.sampled_high ? percent2(item.sampled_low) + " to " + percent2(item.sampled_high) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}

            <div className="grid gap-6 lg:grid-cols-2">
              {simulation.downside_case && (
                <Card title={simulation.downside_case.label} description="Driver values that occurred together in one generated downside case, not individual worst cases.">
                  <Stat label="Levered IRR" value={percent(simulation.downside_case.levered_irr)} tone="critical" />
                  <CaseValues values={simulation.downside_case.values} />
                </Card>
              )}
              {simulation.upside_case && (
                <Card title={simulation.upside_case.label} description="Driver values from one generated upside case.">
                  <Stat label="Levered IRR" value={percent(simulation.upside_case.levered_irr)} tone="good" />
                  <CaseValues values={simulation.upside_case.values} />
                </Card>
              )}
            </div>

            {simulation.sampled_ranges && (
              <Card title="Sampled bands" description="The range each driver was actually drawn from, for the audit trail.">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Driver</th>
                      <th>Distribution</th>
                      <th>Minimum</th>
                      <th>Mode</th>
                      <th>Maximum</th>
                    </tr>
                  </thead>
                  <tbody>
                    {simulation.sampled_ranges.map((band) => (
                      <tr key={band.key}>
                        <td className="font-medium">{SENSITIVITY_LABELS[band.key]}</td>
                        <td className="text-ink-secondary">{titleCase(band.distribution)}</td>
                        <td>{percent2(band.minimum)}</td>
                        <td className="font-semibold">{percent2(band.mode)}</td>
                        <td>{percent2(band.maximum)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            )}
            {simulation.market_context && (
              <p className="text-xs text-ink-muted">
                Calibrated to {simulation.market_context.property_type} · {simulation.market_context.value_bucket} from {simulation.market_context.source} ({simulation.market_context.observations} periods, {simulation.market_context.period_start} to {simulation.market_context.period_end}).
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function CaseValues({ values }: { values: Record<string, string> }) {
  return (
    <ul className="mt-3 space-y-1 text-sm">
      {Object.entries(values).map(([key, value]) => (
        <li key={key} className="flex justify-between gap-3 border-t border-line pt-1 text-ink-secondary">
          <span>{titleCase(key)}</span>
          <span className="tabular font-medium text-ink">{percent2(value)}</span>
        </li>
      ))}
    </ul>
  );
}
