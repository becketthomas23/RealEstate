# CRE Reverse-Solver Underwriting App — MVP Plan

## Product goal

Help an analyst answer: **given a target return and risk constraints, what is the maximum price to pay for a property?**

V1 should be a transparent pricing calculator, rather than a full underwriting platform. It should support one simple, stabilized asset type (for example, multifamily) and annual cash flows.

## V1 user workflow

1. Analyst creates a deal and enters core property, operating, debt, and return assumptions.
2. The application calculates a 5–10 year annual pro forma.
3. The analyst provides a target levered IRR and constraints.
4. The reverse solver finds the maximum purchase price that meets those criteria.
5. The app shows the annual cash flows, sensitivities, and explainable risk flags.

## V1 scope

### Inputs

- Purchase price, closing costs, hold period, and exit cap rate
- Current NOI, rent growth, expense growth, and vacancy
- Loan-to-value, interest rate, and amortization period
- Target levered IRR and minimum DSCR

### Calculations

- 5–10 year annual cash-flow projection
- Debt service and ending loan balance
- Sale proceeds, including selling costs and loan payoff
- Levered IRR, equity multiple, and DSCR
- Maximum purchase price reverse-solved to the target IRR

### Outputs

- Maximum purchase price and recommended bid range
- Annual pro forma
- One-way sensitivity analyses for rent growth, exit cap rate, and interest rate
- Explainable flags, such as weak debt coverage, high leverage, aggressive rent growth, or aggressive exit assumptions

## Recommended technical foundation

```text
Next.js / TypeScript frontend
            |
            v
FastAPI calculation and API layer
            |
            v
PostgreSQL: deals, assumptions, calculation runs, results
```

- **Frontend:** Next.js and TypeScript for a straightforward deal-input form and results dashboard.
- **Backend:** Python and FastAPI; Python is well suited to financial calculations and later optimization/simulation work.
- **Database:** PostgreSQL.
- **Initial file interoperability:** CSV and Excel import/export. An Excel add-in can follow after the core experience is trusted.

## Extensible data model

Keep user-entered assumptions separate from calculated results and version assumptions on every change.

```text
Deal
  └─ AssumptionSet (immutable, versioned)
       └─ CalculationRun
            └─ Result
```

This supports scenario comparison, auditability, collaboration, and later calculation-engine upgrades without rewriting historical deal records.

## Build sequence

### Week 1 — Calculation engine

- Define a documented input/output schema.
- Implement the annual pro forma, debt service, sale proceeds, IRR, equity multiple, and DSCR.
- Add unit tests against hand-calculated example deals.

### Week 2 — Reverse solver and basic application

- Implement maximum-price solving for a target IRR (binary search/root finding is sufficient initially).
- Build a deal creation form and results page.
- Persist deals, assumptions, runs, and results in PostgreSQL.

### Week 3 — Scenarios and risk checks

- Add base, upside, and downside assumption sets.
- Implement simple, transparent rules-based risk flags.
- Add CSV/Excel import and export.

### Week 4 — Analyst usability and validation

- Add sensitivity matrices.
- Improve input validation, assumption history, authentication, and exports.
- Pilot against historical deals and reconcile outputs to existing analyst spreadsheets.

## Data sources

For the initial product, use analyst-entered data and uploads alongside licensed CoStar data. Potential subsequent integrations:

- CompStak for lease, sale, and loan comparables
- MSCI Real Capital Analytics for institutional transaction and capital-market data
- Reonomy for ownership, assessor, debt, and lien enrichment
- FRED for interest-rate and macroeconomic scenarios
- Census Building Permits Survey for multifamily supply signals
- FEMA National Risk Index for location-based risk flags
- Local assessor, recorder, zoning, and permit records

Store each assumption's source, effective date, and confidence level. This makes risk flags defensible and reviewable.

## Explicitly defer from V1

- CoStar API integration and automated document extraction
- Monthly and tenant/lease-level cash flows
- Monte Carlo simulation
- Equity waterfalls, preferred equity, construction draws, and advanced refinancing
- Automated comp-derived recommendations based on sparse or unverified data

## MVP success criterion

An analyst can recreate a familiar simple deal, adjust target return and core assumptions, and receive a credible maximum purchase price in under five minutes.
