"use client";

import { useState } from "react";
import { constraintLabel, money, percent } from "@/lib/format";
import { Badge, Button, Card, EmptyState, KeyValue } from "../ui";
import { hasDetail, type Workspace } from "./useDealWorkspace";

export function ReportsTab({ workspace, onGoToInputs }: { workspace: Workspace; onGoToInputs: () => void }) {
  const { result, deal, activeSet, meta, form, busy, download, simulationOptions, detail } = workspace;
  const [includeSimulation, setIncludeSimulation] = useState(true);
  const [includeSensitivity, setIncludeSensitivity] = useState(true);
  if (!result || !activeSet) {
    return <EmptyState title="Solve a price first" description="Reports describe the solved case for the active version." action={<Button onClick={onGoToInputs}>Go to inputs</Button>} />;
  }
  const detailIncluded = hasDetail(activeSet.supporting_detail ? { ...detail, ...activeSet.supporting_detail } : detail);
  const sheets = [
    ["Summary", "Pricing conclusion, returns, sources and uses, per-unit metrics, annual snapshot, flags, conventions"],
    ["Pro Forma", "Year 0 to forward year with live formula subtotals, DSCR, debt yield, levered and unlevered cash flow, IRR and multiple formulas"],
    ["Monthly Cash Flow", "Every month of the hold with debt service split and loan balance"],
    ["Debt", "Loan summary, annual schedule, monthly amortization"],
    ["Sale & Returns", "Disposition, return attribution, levered versus unlevered, annual return metrics and payback"],
    ...(includeSensitivity ? [["Sensitivity", "IRR, multiple, DSCR and maximum-price grids plus one-way price sensitivity, all at the solved price"]] : []),
    ...(includeSimulation && simulationOptions ? [["Risk Simulation", "Sampled bands, outcome percentiles, probabilities, histogram, tornado data, representative cases"]] : []),
    ...(detailIncluded ? [["Rent Roll & Expenses", "Property facts, rent roll with loss-to-lease, other income, expense detail with per-unit and per-SF"]] : []),
    ["Risk Flags", "Rules, thresholds and observed values"],
    ["Assumptions", "Every input in model units with notes"],
  ];
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
      <Card
        title="Excel underwriting model"
        description="A full analyst workbook built from the audited engine with live formulas for subtotals and returns. Excel recalculates on open."
        actions={
          <Button onClick={() => void download("excel", { includeSimulation: includeSimulation && Boolean(simulationOptions), includeSensitivity })} busy={busy === "export-excel"}>
            Download .xlsx
          </Button>
        }
      >
        <div className="mb-4 grid gap-2 sm:grid-cols-2">
          <label className="flex items-start gap-2 rounded-[var(--radius-control)] border border-line px-3 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary-soft">
            <input type="checkbox" className="mt-1 accent-primary" checked={includeSensitivity} onChange={(event) => setIncludeSensitivity(event.target.checked)} />
            <span>
              <span className="font-medium">Sensitivity grids</span>
              <span className="block text-xs text-ink-muted">Six grids and the one-way table, re-solved at the analysis price.</span>
            </span>
          </label>
          <label className={"flex items-start gap-2 rounded-[var(--radius-control)] border border-line px-3 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary-soft " + (simulationOptions ? "" : "opacity-60")}>
            <input type="checkbox" className="mt-1 accent-primary" checked={includeSimulation && Boolean(simulationOptions)} disabled={!simulationOptions} onChange={(event) => setIncludeSimulation(event.target.checked)} />
            <span>
              <span className="font-medium">Risk simulation</span>
              <span className="block text-xs text-ink-muted">{simulationOptions ? `Re-runs the last setup (${simulationOptions.iterations.toLocaleString()} cases, ${simulationOptions.distribution}) inside the workbook.` : "Run a simulation on the Risk tab first."}</span>
            </span>
          </label>
        </div>
        <ul className="divide-y divide-line text-sm">
          {sheets.map(([name, contents]) => (
            <li key={name} className="flex gap-3 py-2">
              <Badge tone="primary" className="h-fit shrink-0">
                {name}
              </Badge>
              <span className="text-ink-secondary">{contents}</span>
            </li>
          ))}
        </ul>
      </Card>
      <div className="space-y-6">
        <Card title="PDF investment memo" description="Pricing conclusion, return summary, property metrics, annual cash flow, key assumptions, risk review, and the basis of the analysis." actions={<Button variant="secondary" onClick={() => void download("memo")} busy={busy === "export-memo"}>Download .pdf</Button>}>
          <KeyValue
            rows={[
              ["Deal", deal?.name ?? "—"],
              ["Version", `v${activeSet.version} · ${activeSet.label}`],
              ["Source", meta.source || "—"],
              ["Effective date", meta.effective_date],
              ["Confidence", meta.confidence_level],
              ["Target IRR / DSCR floor", `${percent(form.target_levered_irr)} / ${Number(form.minimum_dscr).toFixed(2)}x`],
            ]}
          />
        </Card>
        <Card title="Analysis basis" description="Both reports describe this case.">
          <KeyValue
            rows={[
              ["Analysis price", money(result.maximum_purchase_price)],
              ["Basis", "solved maximum supportable price"],
              ["Binding constraint", constraintLabel(result.binding_constraint)],
              ["Recommended bid range", `${money(result.recommended_bid_floor)} to ${money(result.recommended_bid_ceiling)}`],
              ["Levered IRR", percent(result.underwriting.returns.levered_irr)],
              ["Unlevered IRR", result.underwriting.unlevered?.irr ? percent(result.underwriting.unlevered.irr) : "—"],
            ]}
          />
        </Card>
      </div>
    </div>
  );
}
