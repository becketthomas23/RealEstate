# CRE Reverse-Solver Underwriting App

A transparent commercial real estate underwriting tool that answers:

> Given a target return and risk constraints, what is the maximum price to pay for a property?

> **Educational use only — not financial advice.** This software is a modeling
> and learning tool, not financial, investment, legal, accounting, or tax
> advice. Verify every assumption and calculation independently, and consult
> appropriately qualified professionals before making an investment decision.

This README is a living project document. Update it as the application, technical decisions, and implementation status evolve.

## Project Status

**Current phase:** Advanced underwriting engine and audit workspace

## Latest update

This release expands the original reverse-price solver into a more complete,
auditable underwriting workspace:

- **More rigorous operating and return analysis:** monthly and annual cash
  flows reconcile, recurring cash-on-cash excludes terminal sale proceeds,
  annual rent-growth schedules are supported, all-cash deals report debt
  metrics as not applicable, and ambiguous multi-root IRRs are rejected.
- **Decision and risk tools:** saved-version comparison, one- through
  three-variable sensitivities, seeded Monte Carlo return analysis, historical
  market-driver calibration, and clear per-100-basis-point cash-flow/IRR
  effects.
- **Capital and development workflows:** LP/sponsor preferred-return waterfall,
  construction draw and capitalized-interest schedules, and a
  construction-to-permanent refinance model.
- **Audit-ready interchange:** strict CSV import templates, Excel cash-flow
  workbooks, and PDF investment memos.
- **Usability and launch reliability:** a streamlined recurring-cash-flow view,
  a browser-extension-safe hydration boundary, one-command Windows launchers,
  visible startup diagnostics, and a two-service local smoke test.

### Completed

- [x] Define the MVP product goal and analyst workflow
- [x] Identify the initial technical foundation
- [x] Define the first calculation-engine milestones

### In Progress

- [x] Create the backend calculation structure
- [x] Define calculation input and output schemas
- [x] Implement the annual pro forma, debt, disposition, and returns engines
- [x] Add a composed underwriting calculation workflow
- [x] Implement the bounded maximum-price reverse solver
- [x] Calculate debt amortization monthly and aggregate it into the annual pro forma
- [x] Build the deal input form and results view

### Next Up

- [x] Add unit tests using hand-calculated example deals
- [x] Build the FastAPI calculation interface
- [x] Add persistence for deals, immutable assumption versions, runs, and result snapshots
- [x] Add annual rent-growth schedules and reconciling monthly operating projections
- [x] Add multi-variable sensitivity analysis, reproducible Monte Carlo return risk, and investor waterfalls
- [x] Add construction-loan draw modeling and downloadable Excel/PDF reporting

## MVP Scope

The current calculation engine supports a stabilized asset with annual and
monthly operating cash-flow views, risk simulation, equity waterfalls,
construction-to-permanent financing, and formal exports. The development model
connects construction draws, capitalized interest, permanent refinancing,
stabilized operations, and disposition in one return analysis.

### Inputs

- Purchase price and closing costs
- Hold period and exit cap rate
- Current NOI, rent growth (single rate or annual schedule), expense growth, and vacancy
- Loan-to-value, interest rate, and amortization period
- Target levered IRR and minimum DSCR

### Calculated Outputs

- Annual 5-10 year pro forma plus monthly operating cash-flow view that reconciles to annual totals
- Debt service and ending loan balance
- Sale proceeds, selling costs, and loan payoff
- Going-in cap rate, debt yield, levered IRR, equity multiple, cash-on-cash, and DSCR
- Maximum purchase price that meets the target IRR
- Recommended bid range
- One-way sensitivities for rent growth, exit cap rate, and interest rate
- Two- and three-variable direct-return sensitivity grids
- Seeded Monte Carlo return ranges with confidence-aware assumption bands, correlated market drivers, and representative P10/P90 joint cases
- LP/sponsor preferred-return waterfall allocation
- Monthly construction draws, capitalized interest, and equity requirements
- Development-to-permanent refinance proceeds, shortfalls, and stabilized returns
- Excel cash-flow model and PDF investment memo exports
- Explainable risk flags

### Return conventions

To keep operating yield separate from a terminal disposition, annual
cash-on-cash is calculated as recurring NOI less debt service divided by
initial equity; it excludes sale proceeds. The final-year total equity cash
flow includes the net sale proceeds, and levered IRR and equity multiple use
all equity contributions and distributions.

The engine rejects a cash-flow stream with more than one detected valid IRR
instead of selecting an arbitrary root. In that case, model the interim funding
explicitly or use a metric with stated financing and reinvestment assumptions.

All-cash acquisitions are supported. They carry no debt service or payoff, so
minimum DSCR and debt yield are reported as **N/A — all-cash**, not as zero.

## Planned Architecture

```text
Next.js / TypeScript frontend
            |
            v
FastAPI calculation and API layer
            |
            v
PostgreSQL: deals, assumptions, calculation runs, results
```

Keep user-entered assumptions separate from calculated results and version assumptions on every change:

```text
Deal
  └─ AssumptionSet (immutable, versioned)
       └─ CalculationRun
            └─ Result
```

## Development Setup

From the project root, start the complete local application with one command:

```powershell
.\scripts\start-local.ps1
```

It starts the API and frontend in the background, waits for both to be healthy,
then opens `http://127.0.0.1:3000` in one browser tab. If a new service exits
or does not become ready, the launcher reports separate frontend/backend log
paths in the system temporary directory (`cre-underwriting`), rather than
hiding the cause behind a generic timeout. Use this command when a
PowerShell execution-policy warning appears:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

In VS Code, choose **Terminal > Run Task > Run CRE Underwriting App** for the
same one-click launch. From Windows Explorer, double-click
**Start CRE Underwriting App.cmd** at the project root; it runs the same script
and keeps any startup error visible. Stop both local services with:

```powershell
.\scripts\stop-local.ps1
```

To verify both local services without opening a browser:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\smoke_test.py http://127.0.0.1:8000 --frontend-url http://127.0.0.1:3000
```

## Spreadsheet interchange

Download `GET /v1/imports/underwriting-template` to get the canonical
one-row CSV format, then upload it to `POST /v1/imports/underwriting` for
strict validation before creating an assumption version. The template uses
decimal rates (`0.05` means 5%); optional annual rent-growth values are
semicolon separated. Underwriting results can also be exported as an Excel
cash-flow workbook or PDF investment memo from the workspace.

## Historical market-risk calibration

The return-risk simulation can calibrate relationships among rent growth, exit
cap rates, vacancy, expense growth, and interest rates from an aggregate
historical time series. In the **Market correlation calibration** card, download
the CSV template or call `GET /v1/market-calibrations/template`.

The file must be UTF-8 CSV and use these exact columns:

```text
period,property_type,value_bucket,rent_growth_rate,exit_cap_rate,vacancy_rate,expense_growth_rate,annual_interest_rate
```

Use one consistent frequency—normally quarterly—and decimal rates (`0.05`
means 5%); conventional percentage-formatted values such as `5%` are also
accepted. Each selected property type/value bucket requires at least eight
complete periods; twenty or more quarters is materially more useful and the UI
flags smaller samples. The
preview endpoint (`POST /v1/market-calibrations/preview`) calculates Pearson
correlations plus historical P10/P50/P90 driver ranges for the selected segment
but does not retain the raw file. On a calibrated simulation, the historical
P10/P90 deviation from the segment median is applied around the deal's current
assumption; this preserves the deal-specific base case while using the
historical segment to size the uncertainty band. A
subsequent saved return-risk run retains only the resulting coefficients and
their provenance (source label, source as-of or pull date, segment, time range,
and observation count). The application does not connect to CoStar or any
public-data API in this release: any market history is supplied by the analyst,
and its source label and date are user declarations that should be verified
against the original document or licensed export.

The UI suggests a value bucket from the deal's purchase price. This is a
starting classification, not an appraisal: select the bucket that matches the
historical-market definition used in the source data. Correlations describe
which modeled inputs moved together in the supplied history; they do not prove
causation or make a market forecast. The selected value bucket is a calibration
segment, not a direct predictor of a deal's cash flow or IRR. Each resulting
simulation also reports the sampled association with IRR and cumulative
operating cash flow, plus the controlled one-input-at-a-time change in each per
a 100-basis-point input move. Those effects are deal-specific and explanatory,
not independent causal estimates.

## Data provenance and illustrative defaults

The calculation engine uses the deal assumptions entered by the analyst or
imported through the one-row underwriting CSV. Saved assumption versions record
the source or document reference, effective date, and confidence level. The
market-calibration upload additionally records a source as-of or pull date; the
raw market file is used only for the preview and is not retained.

There are no embedded licensed market data, property comps, CoStar exports, or
public API calls in the current build. The values shown when the app first opens,
the downloadable CSV templates, and test fixtures are illustrative synthetic
examples only. They are not market observations and should be replaced before
using the model for any decision.

## Production deployment

The repository includes a one-service Docker deployment that builds the
frontend into the FastAPI service, so the public site and API share one origin.
It is configured for a managed PostgreSQL database through `DATABASE_URL`;
SQLite remains the local-development default. The recommended free deployment
uses Koyeb for the website and Supabase for PostgreSQL. The deployed site has a
shared-password screen; its password and session secret are deployment secrets,
not repository files.

Follow the complete [Koyeb + Supabase deployment guide](docs/deploy-koyeb-supabase.md).

Planned technologies:

- Frontend: Next.js and TypeScript
- Backend: Python and FastAPI
- Database: PostgreSQL
- Initial file interoperability: CSV and Excel import/export

## Testing and Quality Checks

Every calculation change should include focused tests for:

- Input validation and boundary cases
- Annual operating projections
- Debt service and loan balances
- Sale proceeds and loan payoff
- Levered IRR, equity multiple, and DSCR
- Reverse-solver bounds, convergence, and failure cases
- Risk flags and sensitivity calculations

Before considering a change complete, run the narrowest relevant test or validation command, then the broader test suite when appropriate. Record important commands and known limitations here as the project develops.

GitHub Actions runs the backend suite, migration-drift check, frontend lint,
and production build on every push and pull request.

## Build Sequence

1. **Calculation engine:** schemas, annual pro forma, debt service, sale proceeds, IRR, equity multiple, and DSCR.
2. **Reverse solver and basic application:** maximum-price solving, deal form, results page, and persistence.
3. **Scenarios and risk checks:** base/upside/downside assumptions, transparent risk flags, and imports/exports.
4. **Analyst usability and validation:** sensitivity matrices, assumption history, authentication, exports, and historical deal reconciliation.

## Deferred from V1

- CoStar API integration and automated document extraction
- Multiple pref tiers, promote catch-ups, and multi-investor waterfall structures
- Automated comp-derived recommendations based on sparse or unverified data

## Data and Assumption Standards

For every material assumption, capture:

- Source
- Effective date
- Confidence level
- Assumption-set version

This supports auditability, scenario comparison, collaboration, and explainable risk flags.

Saved assumption versions can be compared in one review through
`POST /v1/deals/{deal_id}/scenario-comparison`. The endpoint applies the same
return and DSCR constraints to every version, returning supportable price,
bid range, return metrics, and risk flags. Versions that cannot satisfy the
solver bracket remain visible with their failure reason.

## Pricing convention

The reverse solver reports the highest price that satisfies the entered return
and debt-coverage constraints. Its recommended bid range is deliberately
transparent: the floor is 95% of that maximum supportable price and the ceiling
is the maximum supportable price itself. Analysts can therefore recognize the
range as a negotiation buffer rather than a second valuation method.

## Product Success Criterion

An analyst can recreate a familiar simple deal, adjust the target return and core assumptions, and receive a credible maximum purchase price in under five minutes.

## Working Notes

Use this section for decisions, open questions, known issues, and implementation notes as the project evolves.

- **Decision:**
- **Open question:**
- **Known issue:**
- **Next decision to make:**


## Site
- https://realestateunderwriting.vercel.app/
