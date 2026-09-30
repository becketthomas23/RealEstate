# CRE Reverse-Solver Underwriting App

A transparent commercial real estate underwriting tool that answers:

> Given a target return and risk constraints, what is the maximum price to pay for a property?

This README is a living project document. Update it as the application, technical decisions, and implementation status evolve.

## Project Status

**Current phase:** Calculation engine and reverse solver

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

## MVP Scope

The first version supports one simple stabilized asset type with annual cash flows.

### Inputs

- Purchase price and closing costs
- Hold period and exit cap rate
- Current NOI, rent growth, expense growth, and vacancy
- Loan-to-value, interest rate, and amortization period
- Target levered IRR and minimum DSCR

### Calculated Outputs

- Annual 5-10 year pro forma
- Debt service and ending loan balance
- Sale proceeds, selling costs, and loan payoff
- Levered IRR, equity multiple, and DSCR
- Maximum purchase price that meets the target IRR
- Recommended bid range
- One-way sensitivities for rent growth, exit cap rate, and interest rate
- Explainable risk flags

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
then opens `http://localhost:3000` in one browser tab. Use this command when a
PowerShell execution-policy warning appears:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

In VS Code, choose **Terminal > Run Task > Run CRE Underwriting App** for the
same one-click launch. Stop both local services with:

```powershell
.\scripts\stop-local.ps1
```

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
- Monthly or tenant/lease-level cash flows
- Monte Carlo simulation
- Equity waterfalls, preferred equity, construction draws, and advanced refinancing
- Automated comp-derived recommendations based on sparse or unverified data

## Data and Assumption Standards

For every material assumption, capture:

- Source
- Effective date
- Confidence level
- Assumption-set version

This supports auditability, scenario comparison, collaboration, and explainable risk flags.

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
