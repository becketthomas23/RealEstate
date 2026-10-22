# CRE Price Solver frontend

The Next.js frontend is the analyst-facing product for the reverse-solver
workflow. It has two screens:

- **Deals** (`/`): the pipeline. Every deal shows its latest version, latest
  solved maximum price, IRR, DSCR, multiple, and risk-flag count. Deals can be
  created, searched, sorted, renamed, and deleted (with confirmation).
- **Deal workspace** (`/deals/?id=…`): a tabbed workspace for one deal.
  - **Inputs** - version details, acquisition and exit, operations (including
    the Year 1 convention and an optional rent-growth schedule), financing, and
    the investment targets. Saving creates an immutable version; re-solving
    unchanged inputs reuses the active version. A one-row CSV can be imported.
  - **Pricing** - the solved maximum price, bid range, binding constraint, key
    metrics, risk flags, an equity cash-flow chart and table, one-way price
    sensitivities, and a two-way IRR grid at the solved price.
  - **Risk** - seeded Monte Carlo at the solved price with optional market
    calibration from an aggregate history CSV.
  - **Capital** - the LP/sponsor waterfall at the solved price with a
    selectable tier order and a year-by-year allocation.
  - **Reports** - Excel workbook and PDF memo exports for the solved case.
  - **History** - every version, every saved run (with the price it
    describes), and a like-for-like comparison across versions.

## Structure

```text
src/app/page.tsx                 Deal list
src/app/deals/page.tsx           Workspace route (Suspense around useSearchParams)
src/app/login/page.tsx           Shared-password screen for protected deployments
src/app/globals.css              Design tokens (@theme) and shared table styles
src/components/ui.tsx            Design-system primitives: Button, Card, Stat, Badge, Tabs, fields…
src/components/shell.tsx         App shell, breadcrumbs, page header
src/components/charts.tsx        Inline SVG cash-flow chart and P10/P90 range bar
src/components/workspace/        useDealWorkspace hook plus one component per tab
src/lib/api.ts                   Typed fetch wrapper and download helper
src/lib/types.ts                 API contracts
src/lib/format.ts                Money, percent, date, and percent-input helpers
src/lib/underwriting.ts          Form <-> API conversions, defaults, version comparison
```

The design system is a small set of tokens in `globals.css` (surfaces, ink,
primary green shared with the exports, status colors, two validated chart
series colors) exposed as Tailwind utilities. New screens should compose the
primitives in `ui.tsx` rather than introducing ad-hoc styles.

## Run locally

Start the backend in a separate terminal:

```powershell
cd ..\backend
uv run backend
```

Then start the frontend:

```powershell
npm install
npm run dev
```

Open `http://localhost:3000`. The frontend calls `http://127.0.0.1:8000` when
served from localhost; set `NEXT_PUBLIC_API_URL` to point elsewhere. In the
one-service Docker deployment the static export is served by the API, so the
same origin is used.

## Checks

```powershell
npm run lint
npx tsc --noEmit
npm run build
```
