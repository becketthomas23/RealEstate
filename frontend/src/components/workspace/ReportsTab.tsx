"use client";

import { constraintLabel, money, percent } from "@/lib/format";
import { Button, Card, EmptyState, KeyValue } from "../ui";
import type { Workspace } from "./useDealWorkspace";

export function ReportsTab({ workspace, onGoToInputs }: { workspace: Workspace; onGoToInputs: () => void }) {
  const { result, deal, activeSet, meta, form, busy, download } = workspace;
  if (!result || !activeSet) {
    return <EmptyState title="Solve a price first" description="Reports describe the solved case for the active version." action={<Button onClick={onGoToInputs}>Go to inputs</Button>} />;
  }
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card title="Excel cash-flow model" description="Summary, annual cash flow with DSCR, risk flags, and assumptions on separate sheets, formatted for review." actions={<Button onClick={() => void download("excel")} busy={busy === "export-excel"}>Download .xlsx</Button>}>
        <ReportBasis workspace={workspace} />
      </Card>
      <Card title="PDF investment memo" description="Pricing conclusion, return summary, annual cash flow, key assumptions, risk review, and the basis of the analysis." actions={<Button onClick={() => void download("memo")} busy={busy === "export-memo"}>Download .pdf</Button>}>
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
    </div>
  );
}

function ReportBasis({ workspace }: { workspace: Workspace }) {
  const { result } = workspace;
  if (!result) return null;
  return (
    <KeyValue
      rows={[
        ["Analysis price", money(result.maximum_purchase_price)],
        ["Basis", "solved maximum supportable price"],
        ["Binding constraint", constraintLabel(result.binding_constraint)],
        ["Recommended bid range", `${money(result.recommended_bid_floor)} to ${money(result.recommended_bid_ceiling)}`],
        ["Levered IRR", percent(result.underwriting.returns.levered_irr)],
      ]}
    />
  );
}
