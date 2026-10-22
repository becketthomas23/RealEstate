"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell, PageHeader } from "@/components/shell";
import { Badge, Banner, Button, Card, ConfirmDialog, EmptyState, Stat, TextInput } from "@/components/ui";
import { api, del, patch, post } from "@/lib/api";
import { constraintLabel, money, multiple, percent, shortDate } from "@/lib/format";
import type { Deal, DealSummary } from "@/lib/types";

type Sort = "updated" | "name" | "price";

export default function DealListPage() {
  const router = useRouter();
  const [deals, setDeals] = useState<DealSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<Sort>("updated");
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [renaming, setRenaming] = useState<{ id: string; name: string } | null>(null);
  const [deleting, setDeleting] = useState<DealSummary | null>(null);

  async function refresh() {
    try {
      setDeals(await api<DealSummary[]>("/v1/deals"));
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load deals.");
      setDeals([]);
    }
  }
  useEffect(() => {
    api<DealSummary[]>("/v1/deals")
      .then((rows) => setDeals(rows))
      .catch((caught: unknown) => {
        setError(caught instanceof Error ? caught.message : "Unable to load deals.");
        setDeals([]);
      });
  }, []);

  const visible = useMemo(() => {
    const list = (deals ?? []).filter((deal) => deal.name.toLowerCase().includes(query.trim().toLowerCase()));
    return [...list].sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name);
      if (sort === "price") return Number(b.latest_pricing?.maximum_purchase_price ?? 0) - Number(a.latest_pricing?.maximum_purchase_price ?? 0);
      return b.updated_at.localeCompare(a.updated_at);
    });
  }, [deals, query, sort]);

  const solved = (deals ?? []).filter((deal) => deal.latest_pricing);
  const pipelineValue = solved.reduce((sum, deal) => sum + Number(deal.latest_pricing?.maximum_purchase_price ?? 0), 0);
  const flagged = solved.filter((deal) => (deal.latest_pricing?.risk_flag_count ?? 0) > 0).length;

  async function createDeal(event: FormEvent) {
    event.preventDefault();
    if (!newName.trim()) return;
    setBusy(true);
    try {
      const deal = await post<Deal>("/v1/deals", { name: newName.trim() });
      router.push("/deals/?id=" + deal.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create the deal.");
      setBusy(false);
    }
  }
  async function saveRename(event: FormEvent) {
    event.preventDefault();
    if (!renaming) return;
    setBusy(true);
    try {
      await patch<Deal>("/v1/deals/" + renaming.id, { name: renaming.name });
      setRenaming(null);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to rename the deal.");
    } finally {
      setBusy(false);
    }
  }
  async function confirmDelete() {
    if (!deleting) return;
    setBusy(true);
    try {
      await del("/v1/deals/" + deleting.id);
      setDeleting(null);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to delete the deal.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell crumbs={[{ label: "Deals" }]}>
      <PageHeader
        title="Deals"
        description="Each deal keeps immutable assumption versions and every solved price, so a bid can always be traced back to the inputs that produced it."
        actions={
          <Button onClick={() => setCreating(true)} size="lg">
            + New deal
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <Banner tone="error" onDismiss={() => setError(null)}>
            {error}
          </Banner>
        </div>
      )}

      <div className="mb-6 grid gap-3 sm:grid-cols-3">
        <Card className="py-4">
          <Stat label="Deals" value={deals ? deals.length : "—"} hint={solved.length + " with a solved price"} />
        </Card>
        <Card className="py-4">
          <Stat label="Solved pipeline" value={money(pipelineValue)} hint="Sum of latest maximum supportable prices" tone="accent" />
        </Card>
        <Card className="py-4">
          <Stat label="With risk flags" value={flagged} hint="Deals whose latest solve raised a flag" tone={flagged ? "warn" : "default"} />
        </Card>
      </div>

      {creating && (
        <Card className="mb-6 rise" title="Create a deal" description="Name the asset; you will enter assumptions on the next screen.">
          <form onSubmit={createDeal} className="flex flex-col gap-3 sm:flex-row">
            <TextInput autoFocus required placeholder="e.g. Maple Street Apartments" value={newName} onChange={(event) => setNewName(event.target.value)} className="flex-1" />
            <div className="flex gap-2">
              <Button type="submit" busy={busy}>
                Create and open
              </Button>
              <Button type="button" variant="ghost" onClick={() => setCreating(false)}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card
        title="Pipeline"
        actions={
          <>
            <TextInput placeholder="Search deals" value={query} onChange={(event) => setQuery(event.target.value)} className="w-48" aria-label="Search deals" />
            <select
              aria-label="Sort deals"
              value={sort}
              onChange={(event) => setSort(event.target.value as Sort)}
              className="h-10 rounded-[var(--radius-control)] border border-line-strong bg-surface px-3 text-sm"
            >
              <option value="updated">Recently updated</option>
              <option value="name">Name</option>
              <option value="price">Solved price</option>
            </select>
          </>
        }
      >
        {deals === null ? (
          <p className="py-10 text-center text-sm text-ink-muted">Loading deals…</p>
        ) : visible.length === 0 ? (
          <EmptyState
            title={deals.length === 0 ? "No deals yet" : "No deals match that search"}
            description={deals.length === 0 ? "Create a deal to start pricing. Each save becomes a numbered, immutable version." : undefined}
            action={deals.length === 0 ? <Button onClick={() => setCreating(true)}>+ New deal</Button> : undefined}
          />
        ) : (
          <div className="-mx-5 overflow-x-auto sm:-mx-6">
            <table className="data-table min-w-[880px]">
              <thead>
                <tr>
                  <th>Deal</th>
                  <th>Latest version</th>
                  <th>Max supportable price</th>
                  <th>Levered IRR</th>
                  <th>Min DSCR</th>
                  <th>Multiple</th>
                  <th>Flags</th>
                  <th>Updated</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {visible.map((deal) => {
                  const pricing = deal.latest_pricing;
                  const version = deal.latest_version;
                  return (
                    <tr key={deal.id} className="cursor-pointer" onClick={() => router.push("/deals/?id=" + deal.id)}>
                      <td>
                        {renaming?.id === deal.id ? (
                          <form onSubmit={saveRename} onClick={(event) => event.stopPropagation()} className="flex items-center gap-2">
                            <TextInput autoFocus value={renaming.name} onChange={(event) => setRenaming({ id: deal.id, name: event.target.value })} className="h-8 w-56" />
                            <Button size="sm" type="submit" busy={busy}>
                              Save
                            </Button>
                            <Button size="sm" type="button" variant="ghost" onClick={() => setRenaming(null)}>
                              Cancel
                            </Button>
                          </form>
                        ) : (
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-ink">{deal.name}</p>
                            <p className="mt-0.5 text-xs text-ink-muted">
                              {version ? version.property_type + " · " + version.value_bucket : "No versions saved"}
                            </p>
                          </div>
                        )}
                      </td>
                      <td className="!text-left">
                        {version ? (
                          <span className="inline-flex items-center gap-2">
                            <Badge tone="primary">v{version.version}</Badge>
                            <span className="text-ink-secondary">{version.label}</span>
                          </span>
                        ) : (
                          <span className="text-ink-muted">—</span>
                        )}
                      </td>
                      <td className="font-semibold text-primary-ink">
                        {pricing ? money(pricing.maximum_purchase_price) : <span className="font-normal text-ink-muted">Not solved</span>}
                        {pricing?.binding_constraint && <p className="text-[11px] font-normal text-ink-muted">bound by {constraintLabel(pricing.binding_constraint)}</p>}
                      </td>
                      <td>{pricing ? percent(pricing.levered_irr) : "—"}</td>
                      <td>{pricing ? (pricing.minimum_dscr === null ? "N/A" : multiple(pricing.minimum_dscr)) : "—"}</td>
                      <td>{pricing ? multiple(pricing.equity_multiple) : "—"}</td>
                      <td>
                        {pricing ? (
                          pricing.risk_flag_count ? <Badge tone="warn">{pricing.risk_flag_count}</Badge> : <Badge tone="good">Clear</Badge>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="text-ink-muted">{shortDate(deal.updated_at)}</td>
                      <td onClick={(event) => event.stopPropagation()}>
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" onClick={() => setRenaming({ id: deal.id, name: deal.name })}>
                            Rename
                          </Button>
                          <Button size="sm" variant="ghost" className="text-critical" onClick={() => setDeleting(deal)}>
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={deleting !== null}
        title={"Delete " + (deleting?.name ?? "this deal") + "?"}
        description={
          deleting
            ? `This permanently removes ${deleting.version_count} saved version${deleting.version_count === 1 ? "" : "s"} and every calculation run. This cannot be undone.`
            : undefined
        }
        confirmLabel="Delete deal"
        busy={busy}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleting(null)}
      />
    </AppShell>
  );
}
