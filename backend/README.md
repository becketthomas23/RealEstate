# Backend calculation architecture

The backend is organized so each financial concern can be repaired or extended
without coupling it to web, database, or other calculation code.

```text
src/backend/
├── core/
│   └── validation.py       # Shared Decimal constants and input validation
└── engines/
    ├── operating/          # Revenue, expenses, vacancy, and NOI
    ├── debt/               # Amortization, debt service, and loan balance
    ├── disposition/        # Sale price, selling costs, and payoff
    └── returns/            # IRR, equity multiple, and DSCR
├── workflows/
│   └── underwriting/       # Composes the engines into deal cash flows
├── solvers/
│   └── pricing/            # Bounded maximum-price binary search
└── api/                    # FastAPI request validation and HTTP endpoints
```

Every engine package follows the same contract:

- `models.py` contains immutable input and result dataclasses.
- `calculator.py` contains the pure calculation functions.
- `__init__.py` is the engine's public API; callers should import from it.

For example:

```python
from backend.engines.debt import DebtAssumptions, project_debt
```

Tests are one file per engine or composed backend capability under `tests/`.
Engines never import each other; the underwriting workflow is the only layer
that composes them. The maximum-price solver calls that workflow, preserving
independently testable, reproducible calculations.

The price solver brackets its own search: starting from the reference purchase
price it doubles until a price fails a constraint (or halves until one passes),
then bisects. Callers may still supply an explicit range whose lower price
meets both constraints and whose upper price fails at least one; that range is
validated rather than silently accepted. The result names the binding
constraint and the bracket that was searched.

## Debt convention

The debt engine calculates a fixed-rate principal-and-interest schedule monthly,
then aggregates each 12-payment period for the annual pro forma, DSCR, and
levered-return views. It uses the stated annual note rate divided by 12 and does
not round individual installments before annual aggregation. This makes loan
payoff at the end of a hold year reflect actual monthly principal reduction while
preserving high-precision `Decimal` calculations. The calculation follows the
standard monthly interest/principal/balance roll-forward described in Fannie
Mae's [manual amortization guide](https://singlefamily.fanniemae.com/job-aid/loan-delivery/topic/loan_delivery_job_aids__how_to_manually_amortize_a_loan.htm).

## Verify

```powershell
uv run python -m unittest discover -s tests -v
```

## Run the API

```powershell
uv run backend
```

The local server runs at `http://127.0.0.1:8000`; interactive API documentation
is available at `/docs`. The calculation endpoints are `POST /v1/underwriting`
and `POST /v1/maximum-price`; `POST /v1/sensitivities` returns one-way
maximum-price cases. Financial values are returned as decimal strings so clients
do not lose precision through floating-point JSON conversion.

Sensitivity analysis changes one input at a time while holding every other
assumption and return constraint fixed:

- Rent growth: lower/base/higher by 100 basis points.
- Exit cap rate: lower/base/higher by 50 basis points.
- Interest rate: lower/base/higher by 100 basis points (never below zero).

Each scenario independently runs the same self-bracketing price solver. A
scenario that cannot be solved is returned as unavailable with its reason; it
does not hide the other cases.

## Persistence and audit history

The API persists the workflow documented in the product plan:

```text
Deal -> immutable AssumptionSet versions -> CalculationRun -> CalculationResult
```

For local development, no setup is required: the API applies its versioned
Alembic schema migration to a SQLite database at `backend/cre_underwriting.db`
on startup. This file is ignored by Git. For PostgreSQL, set `DATABASE_URL`
before starting the API; the included driver uses the SQLAlchemy
`postgresql+psycopg://` URL format.

```powershell
$env:DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/cre_underwriting"
uv run backend
```

Persisted API workflow:

1. `POST /v1/deals` creates a deal.
2. `POST /v1/deals/{deal_id}/assumption-sets` creates the next immutable input version, including source, effective date, and confidence level.
3. `POST /v1/assumption-sets/{id}/underwriting`, `/maximum-price`, or `/sensitivities` calculates and saves a run and its result snapshot.
4. `GET /v1/assumption-sets/{id}/calculation-runs` lists the history; `GET /v1/calculation-runs/{id}` retrieves any saved snapshot.

## Schema migrations

Migrations are stored under `migrations/` and automatically applied on API
startup. To inspect the schema explicitly or add a future revision:

```powershell
uv run alembic current
uv run alembic revision --autogenerate -m "describe the schema change"
uv run alembic upgrade head
```

`uv run alembic check` compares the SQLAlchemy models to the latest migration;
the GitHub Actions workflow runs it to prevent unversioned production schema
changes.
