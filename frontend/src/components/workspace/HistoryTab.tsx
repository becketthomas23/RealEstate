"use client";

import { money, multiple, percent, shortDate, shortDateTime, titleCase } from "@/lib/format";
import { Badge, Button, Card, EmptyState, Stat } from "../ui";
import type { Workspace } from "./useDealWorkspace";

export function HistoryTab({ workspace, onShowRun }: { workspace: Workspace; onShowRun: () => void }) {
  const { deal, activeSet, runs, openSet, showRun, comparison, compareVersions, busy, form } = workspace;
  const versions = deal?.assumption_sets ?? [];

  if (!deal || versions.length === 0) {
    return <EmptyState title="No versions yet" description="Save and solve from the Inputs tab to create version 1. Every later save adds a numbered version here." />;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card title="Versions" description="Inputs are never edited in place. Open a version to load its inputs and latest results.">
          <ul className="space-y-2">
            {versions.map((saved) => {
              const active = activeSet?.id === saved.id;
              return (
                <li key={saved.id}>
                  <button
                    type="button"
                    onClick={() => void openSet(saved)}
                    className={
                      "w-full rounded-[var(--radius-control)] border p-3 text-left transition " +
                      (active ? "border-primary bg-primary-soft" : "border-line hover:border-line-strong hover:bg-surface-muted")
                    }
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="flex items-center gap-2 text-sm font-semibold">
                        <Badge tone={active ? "primary" : "neutral"}>v{saved.version}</Badge>
                        {saved.label}
                      </span>
                      <Badge tone="neutral">{saved.confidence_level} confidence</Badge>
                    </div>
                    <p className="mt-1 truncate text-xs text-ink-muted">
                      {saved.source || "No source recorded"} · effective {saved.effective_date} · {saved.property_type} · {saved.value_bucket} · reference {money(saved.underwriting.purchase_price)}
                    </p>
                  </button>
                </li>
              );
            })}
          </ul>
        </Card>

        <Card title={activeSet ? `Saved runs for v${activeSet.version}` : "Saved runs"} description="Every calculation is retained with the request that produced it. Select one to display it.">
          {runs.length === 0 ? (
            <EmptyState compact title="No runs saved for this version" />
          ) : (
            <ul className="divide-y divide-line">
              {runs.map((run) => (
                <li key={run.id}>
                  <button
                    type="button"
                    onClick={() => {
                      showRun(run);
                      onShowRun();
                    }}
                    className="flex w-full items-center justify-between gap-3 py-2.5 text-left text-sm hover:text-primary-ink"
                  >
                    <span className="flex items-center gap-2">
                      <Badge tone="neutral">{titleCase(run.calculation_type)}</Badge>
                      <span className="text-xs text-ink-muted">{describeRun(run)}</span>
                    </span>
                    <span className="shrink-0 text-xs text-ink-muted">{shortDateTime(run.created_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card
        title="Compare versions"
        description={`Re-solves every version with the current targets (${percent(form.target_levered_irr)} IRR, ${Number(form.minimum_dscr).toFixed(2)}x DSCR) so the versions are compared like for like.`}
        actions={
          <Button variant="secondary" size="sm" onClick={() => void compareVersions()} busy={busy === "compare"} disabled={versions.length < 2}>
            {comparison ? "Re-run comparison" : "Run comparison"}
          </Button>
        }
      >
        {versions.length < 2 ? (
          <p className="text-sm text-ink-muted">Save a second version to compare scenarios side by side.</p>
        ) : !comparison ? (
          <EmptyState compact title="Not run" description="Compare supportable price, returns, and flags across every saved version." />
        ) : (
          <>
            <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Versions" value={comparison.scenarios.length} />
              <Stat label="Highest price" value={money(Math.max(...comparison.scenarios.map((s) => Number(s.maximum_purchase_price ?? 0))))} tone="accent" />
              <Stat label="Lowest price" value={money(Math.min(...comparison.scenarios.filter((s) => s.maximum_purchase_price).map((s) => Number(s.maximum_purchase_price))))} />
              <Stat label="Spread" value={money(Math.max(...comparison.scenarios.map((s) => Number(s.maximum_purchase_price ?? 0))) - Math.min(...comparison.scenarios.filter((s) => s.maximum_purchase_price).map((s) => Number(s.maximum_purchase_price))))} />
            </div>
            <div className="-mx-5 overflow-x-auto sm:-mx-6">
              <table className="data-table min-w-[760px]">
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Confidence</th>
                    <th>Max price</th>
                    <th>Bid range</th>
                    <th>IRR</th>
                    <th>Min DSCR</th>
                    <th>Multiple</th>
                    <th>Flags</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.scenarios.map((scenario) => (
                    <tr key={scenario.assumption_set_id}>
                      <td className="font-medium">
                        <Badge tone={scenario.assumption_set_id === activeSet?.id ? "primary" : "neutral"}>v{scenario.version}</Badge> {scenario.label}
                      </td>
                      <td className="text-ink-secondary">{scenario.confidence_level}</td>
                      <td className="font-semibold text-primary-ink">{scenario.error ? <span className="font-normal text-critical" title={scenario.error}>Unavailable</span> : money(scenario.maximum_purchase_price)}</td>
                      <td className="text-ink-secondary">{scenario.recommended_bid_floor ? money(scenario.recommended_bid_floor) + " – " + money(scenario.recommended_bid_ceiling) : "—"}</td>
                      <td>{percent(scenario.levered_irr)}</td>
                      <td>{scenario.minimum_dscr === null ? "N/A" : multiple(scenario.minimum_dscr)}</td>
                      <td>{multiple(scenario.equity_multiple)}</td>
                      <td>{scenario.risk_flags.length ? <Badge tone="warn">{scenario.risk_flags.length}</Badge> : <Badge tone="good">Clear</Badge>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

function describeRun(run: Workspace["runs"][number]) {
  const request = run.request;
  if (!request) return shortDate(run.created_at);
  const parts: string[] = [];
  if (request.target_levered_irr) parts.push("target " + percent(request.target_levered_irr));
  if (request.minimum_dscr) parts.push(Number(request.minimum_dscr).toFixed(2) + "x DSCR");
  if (request.purchase_price) parts.push("at " + money(request.purchase_price));
  if (request.preferred_return_rate) parts.push(percent(request.preferred_return_rate) + " pref");
  if (request.iterations) parts.push(request.iterations.toLocaleString() + " cases");
  return parts.join(" · ");
}
