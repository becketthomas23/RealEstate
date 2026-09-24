# CRE Price Solver frontend

The Next.js frontend provides the analyst-facing form, version history, and
results dashboard for the reverse-solver workflow. It creates deals, saves an
immutable assumption version with source metadata, then calls the saved
maximum-price calculation endpoint. The dashboard can reopen a deal, inspect
an older input version, and display every saved calculation run.

After a maximum-price result is saved, select **Run analysis** to calculate and
store one-way maximum-price sensitivities for rent growth (±100 bps), exit cap
rate (±50 bps), and interest rate (±100 bps).

## Run locally

Start the backend in a separate terminal:

```powershell
cd ..\backend
uv run backend
```

Then start the frontend:

```powershell
npm run dev
```

Open `http://localhost:3000`. By default, the app uses
`http://127.0.0.1:8000` for the API. Override that address with
`NEXT_PUBLIC_API_URL` when needed.

## Verify

```powershell
npm run lint
npm run build
```
