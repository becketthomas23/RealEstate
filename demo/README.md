# Deal Scope demo kit

Everything needed for a live demonstration, built from one fictional deal so
the packet, the import, the workspace, and the exports all tell the same
story. Every figure, property, market, and firm in these files is invented.

## Files

| File | What it is |
| --- | --- |
| `Maple Street Apartments - Offering Memorandum (mock).pdf` | A 13-page mock broker offering memorandum: cover, disclaimer, executive summary, property description, market overview, rent roll, financial summary, expense detail, capital plan, financing overview, comparables, risk factors, and two appendices. Appendix A is the **Deal Scope Data Sheet** that the app reads directly; Appendix B lists what the model needs. |
| `maple-street-apartments-import.xlsx` | The same deal in the Excel import template (Assumptions, Rent Roll, Other Income, Operating Expenses). |

Regenerate both after changing the generator:

```powershell
cd backend
uv run python scripts/build_demo_packet.py ../demo
```

## What the model needs

Deal Scope builds a complete deal from eleven required inputs; everything
else enriches the output. The packet's Appendix B maps each input to the page
of the memorandum it comes from.

| Input | Required | Where it comes from in a packet |
| --- | --- | --- |
| Purchase price (asking or guide) | Yes | Executive summary |
| Closing costs (%) | Yes | Buyer assumption |
| Hold period (5–10 years) | Yes | Buyer assumption |
| Exit cap rate | Yes | Sale comparables, capital markets context |
| Selling costs (%) | Yes | Buyer assumption |
| Current potential gross income | Yes, or roll up from the rent roll and other income | Rent roll, financial summary |
| Current operating expenses | Yes, or roll up from the expense detail | Operating expense detail |
| Vacancy and credit loss | Yes | Financial summary, leasing history |
| Rent growth and expense growth | Yes | Submarket fundamentals |
| Loan-to-value, interest rate, amortization | Yes | Financing overview |
| Target levered IRR, minimum DSCR | Recommended | Buyer's investment criteria |
| Units, square feet, class, year built | Optional | Property description |
| Rent roll, other income, expense line items | Optional | Rent roll, financial summary |
| Version label, source, effective date, confidence | Recommended | The packet itself |

A typical broker memorandum runs 25 to 60 pages; the information Deal Scope
needs fits on the two-page data sheet. Any packet can be made importable by
appending the blank data sheet (download it from the Inputs tab, or
`GET /v1/imports/data-sheet-template`) with the values filled in.

## Demo script (about eight minutes)

1. **Sign in.** Launch with `.\scripts\start-local.ps1`; it prints the demo
   administrator credentials. The sign-in page states what the product does.
2. **Pipeline.** The Deals page lists every deal with its latest solved price,
   returns, and flags. Create a deal named *Maple Street Apartments*.
3. **Import the packet.** On the Inputs tab choose *Import packet, Excel or
   CSV* and pick the mock offering memorandum PDF. Point out the notice: the
   data sheet was read, income and expenses rolled up from the detail tables,
   and the loss-to-lease warning. Open *Rent roll and expenses* to show the
   line items that arrived, and the quick read on the right.
4. **Solve.** *Save v1 and solve.* The Pricing tab shows the maximum
   supportable price against the $8.5M guidance, the bid range, the binding
   constraint, levered and unlevered returns, per-unit metrics, the cash-flow
   chart, and risk flags. Run the one-way sensitivity and the two-way grid.
5. **Risk.** Run a 2,000-case simulation. Show the probability of meeting the
   target, the loss and DSCR-breach probabilities, the histogram, and the
   tornado.
6. **Capital.** Run the waterfall; show the LP IRR against the deal IRR.
7. **Second version.** Back on Inputs, change the exit cap rate to 7.0%, save
   v2, then open History and run *Compare versions*.
8. **Reports.** Download the Excel model with the sensitivity and simulation
   sheets and open it: Summary, Pro Forma with live formulas, Debt, Sale &
   Returns, Sensitivity, Risk Simulation, Rent Roll & Expenses.
9. **Team.** From the account menu open *Team and access* and add an analyst
   account to show roles and the audit trail (versions record who saved them).

## Example pipeline

`backend/scripts/seed_examples.py` fills the Deals page with seven fictional
deals across multifamily, industrial, retail, office, and self storage, each
with supporting detail, one or two versions, and a solved price, so the
pipeline looks lived-in before the Maple Street walkthrough starts:

```powershell
cd backend
$env:SEED_EMAIL = "admin@dealscope.local"
$env:SEED_PASSWORD = "dealscope-demo"
uv run python scripts/seed_examples.py http://127.0.0.1:8000 --reset
```

`--reset` deletes every existing deal first. Leave it off to add the examples
to whatever is already there. Maple Street Apartments is deliberately not
among them so the live import creates it fresh.

## Resetting between demos

Re-run the seed command above with `--reset`, or delete the demo deal from
the Deals page. The import leaves nothing behind until *Save and solve*.
