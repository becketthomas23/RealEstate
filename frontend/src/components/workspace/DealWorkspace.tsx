"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { money, percent, shortDate } from "@/lib/format";
import { AppShell } from "../shell";
import { Badge, Banner, Button, ConfirmDialog, EmptyState, Tabs, TextInput, type TabItem } from "../ui";
import { CapitalTab } from "./CapitalTab";
import { HistoryTab } from "./HistoryTab";
import { InputsTab } from "./InputsTab";
import { PricingTab } from "./PricingTab";
import { ReportsTab } from "./ReportsTab";
import { RiskTab } from "./RiskTab";
import { useDealWorkspace } from "./useDealWorkspace";

type TabKey = "inputs" | "pricing" | "risk" | "capital" | "reports" | "history";

export function DealWorkspace() {
  const params = useSearchParams();
  const router = useRouter();
  const dealId = params.get("id");
  const workspace = useDealWorkspace(dealId);
  const { deal, loadingDeal, notFound, activeSet, result, dirty, error, setError, notice, setNotice, busy, renameDeal, deleteDeal, simulation, waterfall } = workspace;
  const [tab, setTab] = useState<TabKey>("inputs");
  const [renaming, setRenaming] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [autoAdvanced, setAutoAdvanced] = useState(false);

  // After the first solve of a session, land on the pricing tab once.
  if (result && !autoAdvanced && tab === "inputs" && busy === null && notice?.includes("solved")) {
    setAutoAdvanced(true);
    setTab("pricing");
  }

  const tabs: TabItem<TabKey>[] = [
    { key: "inputs", label: "Inputs", badge: dirty ? <Badge tone="warn">Unsaved</Badge> : undefined },
    { key: "pricing", label: "Pricing", badge: result ? <Badge tone="primary">{money(result.maximum_purchase_price)}</Badge> : undefined },
    { key: "risk", label: "Risk", badge: simulation ? <Badge tone="neutral">Run</Badge> : undefined },
    { key: "capital", label: "Capital", badge: waterfall ? <Badge tone="neutral">Run</Badge> : undefined },
    { key: "reports", label: "Reports" },
    { key: "history", label: "History", badge: deal?.assumption_sets.length ? <Badge tone="neutral">{deal.assumption_sets.length}</Badge> : undefined },
  ];

  async function submitRename(event: FormEvent) {
    event.preventDefault();
    if (renaming?.trim()) await renameDeal(renaming.trim());
    setRenaming(null);
  }
  async function confirmDelete() {
    const done = await deleteDeal();
    if (done) router.push("/");
  }

  if (notFound) {
    return (
      <AppShell crumbs={[{ label: "Deals", href: "/" }, { label: "Not found" }]}>
        <EmptyState title="That deal could not be found" description="It may have been deleted, or the link is incomplete." action={<Button onClick={() => router.push("/")}>Back to deals</Button>} />
      </AppShell>
    );
  }

  return (
    <AppShell
      crumbs={[{ label: "Deals", href: "/" }, { label: deal?.name ?? "Loading…" }]}
      actions={
        deal && (
          <>
            <Button variant="ghost" size="sm" onClick={() => setRenaming(deal.name)}>
              Rename
            </Button>
            <Button variant="ghost" size="sm" className="text-critical" onClick={() => setConfirmingDelete(true)}>
              Delete
            </Button>
          </>
        )
      }
    >
      {loadingDeal ? (
        <p className="py-20 text-center text-sm text-ink-muted">Loading deal…</p>
      ) : (
        <>
          <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="min-w-0">
              {renaming !== null ? (
                <form onSubmit={submitRename} className="flex items-center gap-2">
                  <TextInput autoFocus value={renaming} onChange={(event) => setRenaming(event.target.value)} className="h-11 w-80 text-lg font-semibold" />
                  <Button type="submit" busy={busy === "rename"}>
                    Save
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => setRenaming(null)}>
                    Cancel
                  </Button>
                </form>
              ) : (
                <h1 className="truncate text-2xl font-semibold tracking-tight sm:text-3xl">{deal?.name}</h1>
              )}
              <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-ink-secondary">
                {activeSet ? (
                  <>
                    <Badge tone="primary">v{activeSet.version}</Badge>
                    <span>{activeSet.label}</span>
                    <span className="text-ink-muted">·</span>
                    <span>{activeSet.property_type}</span>
                    <span className="text-ink-muted">·</span>
                    <span>{activeSet.value_bucket}</span>
                    <span className="text-ink-muted">·</span>
                    <span>effective {shortDate(activeSet.effective_date)}</span>
                  </>
                ) : (
                  <span>No versions saved yet. Enter the assumptions and solve to create v1.</span>
                )}
              </p>
            </div>
            {result && (
              <div className="flex items-center gap-5 rounded-[var(--radius-card)] border border-line bg-surface px-4 py-3 shadow-[var(--shadow-card)]">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted">Max supportable price</p>
                  <p className="tabular text-xl font-semibold text-primary-ink">{money(result.maximum_purchase_price)}</p>
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted">Levered IRR</p>
                  <p className="tabular text-xl font-semibold">{percent(result.underwriting.returns.levered_irr)}</p>
                </div>
              </div>
            )}
          </div>

          <div className="mb-6 border-b border-line">
            <Tabs items={tabs} value={tab} onChange={setTab} />
          </div>

          <div className="mb-4 space-y-3">
            {error && (
              <Banner tone="error" onDismiss={() => setError(null)}>
                {error}
              </Banner>
            )}
            {notice && (
              <Banner tone="success" onDismiss={() => setNotice(null)}>
                {notice}
              </Banner>
            )}
            {dirty && tab !== "inputs" && activeSet && (
              <Banner tone="info">
                The inputs have unsaved changes. Results on this tab describe v{activeSet.version} as saved; save and solve from Inputs to update them.
              </Banner>
            )}
          </div>

          {tab === "inputs" && <InputsTab workspace={workspace} />}
          {tab === "pricing" && <PricingTab workspace={workspace} onGoToInputs={() => setTab("inputs")} />}
          {tab === "risk" && <RiskTab workspace={workspace} onGoToInputs={() => setTab("inputs")} />}
          {tab === "capital" && <CapitalTab workspace={workspace} onGoToInputs={() => setTab("inputs")} />}
          {tab === "reports" && <ReportsTab workspace={workspace} onGoToInputs={() => setTab("inputs")} />}
          {tab === "history" && <HistoryTab workspace={workspace} onShowRun={() => setTab("pricing")} />}
        </>
      )}

      <ConfirmDialog
        open={confirmingDelete}
        title={"Delete " + (deal?.name ?? "this deal") + "?"}
        description="This permanently removes every saved version and calculation run for the deal. This cannot be undone."
        confirmLabel="Delete deal"
        busy={busy === "delete"}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setConfirmingDelete(false)}
      />
    </AppShell>
  );
}
