"use client";

import { useState } from "react";
import { fromPercentText, money, multiple, percent, toPercentText } from "@/lib/format";
import { Banner, Button, Card, EmptyState, Field, NumberField, Select, Stat } from "../ui";
import type { Workspace } from "./useDealWorkspace";

export function CapitalTab({ workspace, onGoToInputs }: { workspace: Workspace; onGoToInputs: () => void }) {
  const { result, waterfall, waterfallPrice, busy, runWaterfall } = workspace;
  const [preferredReturn, setPreferredReturn] = useState("0.08");
  const [sponsorShare, setSponsorShare] = useState("0.20");
  const [prefBeforeCapital, setPrefBeforeCapital] = useState(true);

  if (!result) {
    return <EmptyState title="Solve a price first" description="The waterfall allocates the equity cash flow at the solved maximum price between the LP and the sponsor." action={<Button onClick={onGoToInputs}>Go to inputs</Button>} />;
  }
  const stale = waterfall && waterfallPrice && waterfallPrice !== result.maximum_purchase_price;
  const dealIrr = Number(result.underwriting.returns.levered_irr);

  return (
    <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
      <Card title="LP / sponsor structure" description={"Single LP funds the equity (" + money(result.underwriting.initial_equity) + ") at the solved price. Pref accrues yearly on outstanding LP capital, including capital-call years, and carries forward unpaid."}>
        <div className="grid gap-4">
          <Field label="Tier order">
            <Select value={prefBeforeCapital ? "pref_first" : "capital_first"} onChange={(event) => setPrefBeforeCapital(event.target.value === "pref_first")}>
              <option value="pref_first">Accrued pref, then return of capital, then split</option>
              <option value="capital_first">Return of capital, then accrued pref, then split</option>
            </Select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <NumberField label="Preferred return" suffix="%" min="0" value={toPercentText(preferredReturn)} onChange={(value) => setPreferredReturn(fromPercentText(value))} />
            <NumberField label="Sponsor promote" suffix="%" min="0" value={toPercentText(sponsorShare)} onChange={(value) => setSponsorShare(fromPercentText(value))} help="Sponsor share of residual cash flow." />
          </div>
        </div>
        <Button className="mt-5 w-full" onClick={() => void runWaterfall({ preferredReturn, sponsorShare, prefBeforeCapital })} busy={busy === "waterfall"}>
          {waterfall ? "Re-run waterfall" : "Run waterfall"}
        </Button>
      </Card>

      <div className="space-y-6">
        {!waterfall ? (
          <EmptyState title="No waterfall for this version" description="Set the preferred return and promote, then run. The allocation is saved with the version and the price it describes." />
        ) : (
          <>
            {stale && (
              <Banner tone="info">
                This waterfall describes a price of {money(waterfallPrice)}; the current solved price is {money(result.maximum_purchase_price)}. Re-run to update it.
              </Banner>
            )}
            <Card title="Distribution summary" description={`At ${money(waterfallPrice ?? result.maximum_purchase_price)} · ${waterfall.pay_preferred_return_before_capital === false ? "capital returned before pref" : "pref paid before capital"}.`}>
              <div className="grid grid-cols-2 gap-5 sm:grid-cols-4">
                <Stat label="LP IRR" value={percent(waterfall.lp_irr)} hint={"deal IRR " + percent(dealIrr)} tone="accent" />
                <Stat label="LP multiple" value={multiple(waterfall.lp_equity_multiple)} hint={"on " + money(waterfall.total_lp_contributed)} />
                <Stat label="LP distributions" value={money(waterfall.total_lp_distributed)} />
                <Stat label="Sponsor promote" value={money(waterfall.total_sponsor_distributed)} hint={percent(Number(waterfall.total_sponsor_distributed) / (Number(waterfall.total_sponsor_distributed) + Number(waterfall.total_lp_distributed) || 1)) + " of distributions"} />
              </div>
            </Card>
            <Card title="Annual allocation">
              <div className="-mx-5 overflow-x-auto sm:-mx-6">
                <table className="data-table min-w-[760px]">
                  <thead>
                    <tr>
                      <th>Year</th>
                      <th>Property CF</th>
                      <th>LP call</th>
                      <th>Pref accrued</th>
                      <th>Pref paid</th>
                      <th>Capital returned</th>
                      <th>LP residual</th>
                      <th>Sponsor</th>
                      <th>Unpaid pref</th>
                      <th>Unreturned capital</th>
                    </tr>
                  </thead>
                  <tbody>
                    {waterfall.years.map((year) => (
                      <tr key={year.year}>
                        <td className="font-medium">{year.year}</td>
                        <td className={Number(year.property_cash_flow) < 0 ? "text-critical" : ""}>{money(year.property_cash_flow)}</td>
                        <td>{Number(year.lp_capital_contribution) ? money(year.lp_capital_contribution) : "—"}</td>
                        <td className="text-ink-secondary">{year.accrued_preferred_return ? money(year.accrued_preferred_return) : "—"}</td>
                        <td>{money(year.preferred_return_to_lp)}</td>
                        <td>{money(year.return_of_capital_to_lp)}</td>
                        <td>{money(year.residual_to_lp)}</td>
                        <td className="font-semibold text-primary-ink">{money(year.sponsor_distribution)}</td>
                        <td className="text-ink-secondary">{money(year.unpaid_preferred_return)}</td>
                        <td className="text-ink-secondary">{money(year.unreturned_lp_capital)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
