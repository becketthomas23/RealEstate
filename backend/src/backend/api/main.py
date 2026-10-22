"""FastAPI application for the CRE reverse-solver backend."""

from contextlib import asynccontextmanager
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Generator

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from backend.engines.operating import OperatingAssumptions
from backend.solvers.pricing import MaximumPriceAssumptions, solve_maximum_purchase_price
from backend.workflows.sensitivity import (
    AdvancedSensitivityAssumptions,
    AdvancedSensitivityDimension,
    SensitivityAssumptions,
    calculate_advanced_sensitivity,
    calculate_one_way_sensitivities,
)
from backend.workflows.underwriting import UnderwritingAssumptions, calculate_underwriting
from dataclasses import replace
from backend.workflows.monte_carlo import Correlation, MarketContext, MonteCarloAssumptions, SimulationVariable, calculate_monte_carlo
from backend.workflows.monte_carlo.calibration import calculate_market_calibration, market_calibration_csv_template
from backend.engines.waterfall import WaterfallAssumptions, calculate_waterfall
from backend.engines.construction import ConstructionLoanAssumptions, project_construction_loan
from backend.workflows.development import DevelopmentAssumptions, calculate_development
from backend.reports import excel_cash_flow, investment_memo
from backend.imports import parse_underwriting_csv, underwriting_csv_template
from backend.persistence import Database, Repository
from backend.persistence.models import AssumptionSetRecord, CalculationRunRecord, DealRecord
from .access import (
    SESSION_COOKIE_NAME,
    SESSION_LIFETIME_SECONDS,
    access_is_required,
    cookie_requires_https,
    create_session_token,
    password_is_valid,
    session_is_valid,
    validate_access_configuration,
)

from .schemas import (
    AssumptionSetCreateRequest,
    AdvancedSensitivityRequest,
    DealCreateRequest,
    LoginRequest,
    MaximumPriceRequest,
    OperatingAssumptionsRequest,
    SavedMaximumPriceRequest,
    SavedMonteCarloRequest,
    SavedSensitivityRequest,
    SavedWaterfallRequest,
    ScenarioComparisonRequest,
    SensitivityRequest,
    MonteCarloRequest,
    WaterfallRequest,
    ConstructionLoanRequest,
    DevelopmentRequest,
    ExportRequest,
    UnderwritingRequest,
)


database = Database()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_access_configuration()
    database.upgrade_schema()
    yield
    database.dispose()


app = FastAPI(
    title="CRE Reverse-Solver Underwriting API",
    version="0.1.0",
    description="Transparent annual stabilized-property underwriting calculations.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class AccessMiddleware(BaseHTTPMiddleware):
    """Require a signed browser session when protected deployment mode is enabled."""

    public_paths = {"/health", "/login", "/login/", "/v1/auth/login", "/v1/auth/logout", "/v1/auth/session", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not access_is_required() or path in self.public_paths or path.startswith("/_next/"):
            return await call_next(request)
        if session_is_valid(request.cookies.get(SESSION_COOKIE_NAME)):
            return await call_next(request)
        if path.startswith("/v1/"):
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "password required"})
        return RedirectResponse(url="/login/", status_code=status.HTTP_303_SEE_OTHER)


app.add_middleware(AccessMiddleware)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/auth/session", tags=["access"])
def access_session(request: Request) -> dict[str, bool]:
    return {"authenticated": not access_is_required() or session_is_valid(request.cookies.get(SESSION_COOKIE_NAME))}


@app.post("/v1/auth/login", tags=["access"])
def login(request: LoginRequest, response: Response) -> dict[str, bool]:
    if not access_is_required() or not password_is_valid(request.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid password")
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(),
        max_age=SESSION_LIFETIME_SECONDS,
        httponly=True,
        secure=cookie_requires_https(),
        samesite="lax",
        path="/",
    )
    return {"authenticated": True}


@app.post("/v1/auth/logout", tags=["access"])
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"authenticated": False}


def get_session() -> Generator[Session, None, None]:
    yield from database.session()


@app.post("/v1/underwriting", tags=["calculations"])
def underwrite(request: UnderwritingRequest) -> dict[str, Any]:
    """Calculate operating cash flow, debt, sale proceeds, and return metrics."""
    try:
        result = calculate_underwriting(_to_underwriting_assumptions(request))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _serialize(result)


@app.post("/v1/maximum-price", tags=["calculations"])
def maximum_price(request: MaximumPriceRequest) -> dict[str, Any]:
    """Solve the maximum purchase price within a caller-supplied price bracket."""
    try:
        result = solve_maximum_purchase_price(
            MaximumPriceAssumptions(
                underwriting=_to_underwriting_assumptions(request.underwriting),
                target_levered_irr=request.target_levered_irr,
                minimum_dscr=request.minimum_dscr,
                minimum_purchase_price=request.minimum_purchase_price,
                maximum_purchase_price=request.maximum_purchase_price,
                price_tolerance=request.price_tolerance,
                max_iterations=request.max_iterations,
            )
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _serialize(result)


@app.post("/v1/sensitivities", tags=["calculations"])
def sensitivities(request: SensitivityRequest) -> dict[str, Any]:
    """Calculate one-way maximum-price sensitivities for the core rate assumptions."""
    try:
        result = calculate_one_way_sensitivities(
            _to_sensitivity_assumptions(request, _to_underwriting_assumptions(request.underwriting))
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _serialize(result)


@app.post("/v1/advanced-sensitivities", tags=["calculations"])
def advanced_sensitivities(request: AdvancedSensitivityRequest) -> dict[str, Any]:
    """Calculate a one-, two-, or three-variable direct-return sensitivity grid."""
    try:
        result = calculate_advanced_sensitivity(
            AdvancedSensitivityAssumptions(
                underwriting=_to_underwriting_assumptions(request.underwriting),
                dimensions=tuple(
                    AdvancedSensitivityDimension(item.key, tuple(item.values)) for item in request.dimensions
                ),
                metric=request.metric,
            )
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _serialize(result)


@app.post("/v1/monte-carlo", tags=["calculations"])
def monte_carlo(request: MonteCarloRequest) -> dict[str, Any]:
    """Run a seeded, confidence-aware Monte Carlo return simulation."""
    try:
        result = calculate_monte_carlo(_to_monte_carlo_assumptions(request, _to_underwriting_assumptions(request.underwriting)))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _serialize(result)


@app.get("/v1/market-calibrations/template", tags=["calculations"])
def market_calibration_template() -> StreamingResponse:
    """Download the aggregate historical data format used for risk calibration."""
    return StreamingResponse(
        iter([market_calibration_csv_template()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=market-calibration-template.csv"},
    )


@app.post("/v1/market-calibrations/preview", tags=["calculations"])
async def preview_market_calibration(
    file: UploadFile = File(...),
    property_type: str = Form(...),
    value_bucket: str = Form(...),
    source: str = Form("Historical market CSV"),
    source_as_of_date: date = Form(...),
) -> dict[str, Any]:
    """Calculate correlations from a user-supplied aggregate market time series.

    The data is only used to produce this preview response; it is not persisted.
    """
    try:
        calibration = calculate_market_calibration(
            await file.read(), property_type, value_bucket, source, source_as_of_date.isoformat()
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _serialize(calibration)


@app.post("/v1/waterfall", tags=["calculations"])
def waterfall(request: WaterfallRequest) -> dict[str, Any]:
    """Allocate underwriting cash flow through the standard LP/sponsor waterfall."""
    try:
        underwriting = _to_underwriting_assumptions(request.underwriting)
        result = calculate_waterfall(
            WaterfallAssumptions(
                initial_lp_equity=underwriting.initial_equity,
                annual_property_cash_flows=calculate_underwriting(underwriting).annual_cash_flows,
                preferred_return_rate=request.preferred_return_rate,
                sponsor_residual_share=request.sponsor_residual_share,
                pay_preferred_return_before_capital=request.pay_preferred_return_before_capital,
            )
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _serialize(result)


@app.post("/v1/construction-loan", tags=["calculations"])
def construction_loan(request: ConstructionLoanRequest) -> dict[str, Any]:
    """Calculate construction draws, equity needs, fees, and capitalized interest."""
    try:
        result = project_construction_loan(
            ConstructionLoanAssumptions(
                monthly_project_costs=tuple(request.monthly_project_costs),
                loan_to_cost=request.loan_to_cost,
                annual_interest_rate=request.annual_interest_rate,
                origination_fee_rate=request.origination_fee_rate,
            )
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _serialize(result)


@app.post("/v1/development", tags=["calculations"])
def development(request: DevelopmentRequest) -> dict[str, Any]:
    """Underwrite construction draws through permanent financing and sale."""
    try:
        result = calculate_development(_to_development_assumptions(request))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _serialize(result)


@app.get("/v1/imports/underwriting-template", tags=["imports"])
def underwriting_import_template() -> Response:
    """Download a one-row underwriting CSV template with decimal rate inputs."""
    return Response(
        content=underwriting_csv_template(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=underwriting-template.csv"},
    )


@app.post("/v1/imports/underwriting", tags=["imports"])
async def import_underwriting(file: UploadFile = File(...)) -> dict[str, Any]:
    """Validate one spreadsheet-export row before an analyst creates a version."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="upload a .csv underwriting file")
    try:
        request = parse_underwriting_csv(await file.read())
        _to_underwriting_assumptions(request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return {"underwriting": _serialize(request.model_dump())}


@app.post("/v1/exports/excel", tags=["exports"])
def export_excel(request: ExportRequest):
    """Export the case at the request's purchase price with any reporting context."""
    assumptions, result, report = _export_inputs(request)
    return StreamingResponse(
        excel_cash_flow(result, assumptions, report),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=underwriting-cash-flow.xlsx"},
    )


@app.post("/v1/exports/memo", tags=["exports"])
def export_memo(request: ExportRequest):
    """Export an investment memo for the case at the request's purchase price."""
    assumptions, result, report = _export_inputs(request)
    return StreamingResponse(
        investment_memo(result, assumptions, report),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=investment-memo.pdf"},
    )


def _export_inputs(request: ExportRequest):
    try:
        assumptions = _to_underwriting_assumptions(UnderwritingRequest.model_validate(request.model_dump(exclude={"report"})))
        result = calculate_underwriting(assumptions)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    report = request.report.model_dump() if request.report is not None else None
    return assumptions, result, report


@app.post("/v1/deals", tags=["deals"], status_code=status.HTTP_201_CREATED)
def create_deal(request: DealCreateRequest, session: Session = Depends(get_session)) -> dict[str, Any]:
    """Create a deal container for immutable assumption-set versions."""
    return _serialize_deal(Repository(session).create_deal(request.name))


@app.get("/v1/deals", tags=["deals"])
def list_deals(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    return [_serialize_deal(deal) for deal in Repository(session).list_deals()]


@app.get("/v1/deals/{deal_id}", tags=["deals"])
def get_deal(deal_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    deal = _require_deal(Repository(session), deal_id)
    return {
        **_serialize_deal(deal),
        "assumption_sets": [_serialize_assumption_set(item) for item in Repository(session).list_assumption_sets(deal.id)],
    }


@app.post("/v1/deals/{deal_id}/scenario-comparison", tags=["deals"])
def compare_deal_scenarios(
    deal_id: str,
    request: ScenarioComparisonRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Apply one set of investment constraints to every saved deal version.

    A failed solver bracket remains in the comparison with its explanation,
    rather than silently excluding an unfavorable scenario from the review.
    """
    repository = Repository(session)
    _require_deal(repository, deal_id)
    scenarios = []
    for assumption_set in repository.list_assumption_sets(deal_id):
        try:
            result = solve_maximum_purchase_price(
                MaximumPriceAssumptions(
                    underwriting=_stored_underwriting_assumptions(assumption_set),
                    **request.model_dump(),
                )
            )
        except ValueError as error:
            scenarios.append(
                {
                    "assumption_set_id": assumption_set.id,
                    "version": assumption_set.version,
                    "label": assumption_set.label,
                    "confidence_level": assumption_set.confidence_level,
                    "maximum_purchase_price": None,
                    "recommended_bid_floor": None,
                    "recommended_bid_ceiling": None,
                    "levered_irr": None,
                    "minimum_dscr": None,
                    "equity_multiple": None,
                    "risk_flags": [],
                    "error": str(error),
                }
            )
        else:
            scenarios.append(
                {
                    "assumption_set_id": assumption_set.id,
                    "version": assumption_set.version,
                    "label": assumption_set.label,
                    "confidence_level": assumption_set.confidence_level,
                    "maximum_purchase_price": result.maximum_purchase_price,
                    "recommended_bid_floor": result.recommended_bid_floor,
                    "recommended_bid_ceiling": result.recommended_bid_ceiling,
                    "levered_irr": result.underwriting.returns.levered_irr,
                    "minimum_dscr": result.underwriting.returns.minimum_dscr,
                    "equity_multiple": result.underwriting.returns.equity_multiple,
                    "risk_flags": result.underwriting.risk_flags,
                    "error": None,
                }
            )
    return _serialize({"constraints": request.model_dump(), "scenarios": scenarios})


@app.post("/v1/deals/{deal_id}/assumption-sets", tags=["deals"], status_code=status.HTTP_201_CREATED)
def create_assumption_set(
    deal_id: str,
    request: AssumptionSetCreateRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Version a deal's inputs; existing versions are never edited."""
    repository = Repository(session)
    deal = _require_deal(repository, deal_id)
    try:
        _to_underwriting_assumptions(request.underwriting)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    assumptions = repository.create_assumption_set(
        deal=deal,
        label=request.label,
        source=request.source,
        effective_date=request.effective_date,
        confidence_level=request.confidence_level,
        property_type=request.property_type,
        value_bucket=request.value_bucket,
        inputs=_serialize(request.underwriting.model_dump()),
    )
    return _serialize_assumption_set(assumptions)


@app.get("/v1/assumption-sets/{assumption_set_id}", tags=["deals"])
def get_assumption_set(assumption_set_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    assumptions = _require_assumption_set(Repository(session), assumption_set_id)
    return _serialize_assumption_set(assumptions)


@app.get("/v1/assumption-sets/{assumption_set_id}/calculation-runs", tags=["deals"])
def list_calculation_runs(assumption_set_id: str, session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    repository = Repository(session)
    _require_assumption_set(repository, assumption_set_id)
    return [_serialize_run(run) for run in repository.list_runs(assumption_set_id)]


@app.post("/v1/assumption-sets/{assumption_set_id}/underwriting", tags=["deals"], status_code=status.HTTP_201_CREATED)
def calculate_saved_underwriting(
    assumption_set_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Calculate and persist an underwriting result for an immutable input version."""
    repository = Repository(session)
    assumptions = _require_assumption_set(repository, assumption_set_id)
    try:
        result = calculate_underwriting(_stored_underwriting_assumptions(assumptions))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    serialized_result = _serialize(result)
    run = repository.create_completed_run(
        assumption_set=assumptions,
        calculation_type="underwriting",
        request={"underwriting": assumptions.inputs},
        result=serialized_result,
    )
    return {"calculation_run": _serialize_run(run), "result": serialized_result}


@app.post("/v1/assumption-sets/{assumption_set_id}/maximum-price", tags=["deals"], status_code=status.HTTP_201_CREATED)
def calculate_saved_maximum_price(
    assumption_set_id: str,
    request: SavedMaximumPriceRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Solve and persist a target-return maximum price for a saved assumption version."""
    repository = Repository(session)
    assumptions = _require_assumption_set(repository, assumption_set_id)
    try:
        result = solve_maximum_purchase_price(
            MaximumPriceAssumptions(
                underwriting=_stored_underwriting_assumptions(assumptions),
                **request.model_dump(),
            )
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    serialized_result = _serialize(result)
    serialized_request = _serialize(request.model_dump())
    run = repository.create_completed_run(
        assumption_set=assumptions,
        calculation_type="maximum_price",
        request=serialized_request,
        result=serialized_result,
    )
    return {"calculation_run": _serialize_run(run), "result": serialized_result}


@app.post("/v1/assumption-sets/{assumption_set_id}/sensitivities", tags=["deals"], status_code=status.HTTP_201_CREATED)
def calculate_saved_sensitivities(
    assumption_set_id: str,
    request: SavedSensitivityRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Calculate and retain a one-way sensitivity result for an input version."""
    repository = Repository(session)
    assumptions = _require_assumption_set(repository, assumption_set_id)
    try:
        result = calculate_one_way_sensitivities(
            _to_sensitivity_assumptions(request, _stored_underwriting_assumptions(assumptions))
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    serialized_result = _serialize(result)
    run = repository.create_completed_run(
        assumption_set=assumptions,
        calculation_type="sensitivity",
        request=_serialize(request.model_dump()),
        result=serialized_result,
    )
    return {"calculation_run": _serialize_run(run), "result": serialized_result}


@app.post("/v1/assumption-sets/{assumption_set_id}/monte-carlo", tags=["deals"], status_code=status.HTTP_201_CREATED)
def calculate_saved_monte_carlo(
    assumption_set_id: str,
    request: SavedMonteCarloRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Simulate an immutable assumption version and retain its exact risk case."""
    repository = Repository(session)
    assumptions = _require_assumption_set(repository, assumption_set_id)
    try:
        result = calculate_monte_carlo(
            _to_monte_carlo_assumptions(request, _stored_underwriting_assumptions(assumptions, request.purchase_price))
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    serialized_result = _serialize(result)
    run = repository.create_completed_run(
        assumption_set=assumptions,
        calculation_type="monte_carlo",
        request=_serialize(request.model_dump()),
        result=serialized_result,
    )
    return {"calculation_run": _serialize_run(run), "result": serialized_result}


@app.post("/v1/assumption-sets/{assumption_set_id}/waterfall", tags=["deals"], status_code=status.HTTP_201_CREATED)
def calculate_saved_waterfall(
    assumption_set_id: str,
    request: SavedWaterfallRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Allocate a saved version's property cash flow and retain the distribution case."""
    repository = Repository(session)
    assumptions = _require_assumption_set(repository, assumption_set_id)
    try:
        underwriting = _stored_underwriting_assumptions(assumptions, request.purchase_price)
        result = calculate_waterfall(
            WaterfallAssumptions(
                initial_lp_equity=underwriting.initial_equity,
                annual_property_cash_flows=calculate_underwriting(underwriting).annual_cash_flows,
                preferred_return_rate=request.preferred_return_rate,
                sponsor_residual_share=request.sponsor_residual_share,
                pay_preferred_return_before_capital=request.pay_preferred_return_before_capital,
            )
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    serialized_result = _serialize(result)
    run = repository.create_completed_run(
        assumption_set=assumptions,
        calculation_type="waterfall",
        request=_serialize(request.model_dump()),
        result=serialized_result,
    )
    return {"calculation_run": _serialize_run(run), "result": serialized_result}


@app.get("/v1/calculation-runs/{run_id}", tags=["deals"])
def get_calculation_run(run_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    run = Repository(session).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="calculation run not found")
    return _serialize_run(run)


def _to_underwriting_assumptions(request: UnderwritingRequest) -> UnderwritingAssumptions:
    return UnderwritingAssumptions(
        **request.model_dump(exclude={"operating"}),
        operating=_to_operating_assumptions(request.operating),
    )


def _to_operating_assumptions(request: OperatingAssumptionsRequest) -> OperatingAssumptions:
    return OperatingAssumptions(**request.model_dump())


def _to_monte_carlo_assumptions(request: Any, underwriting: UnderwritingAssumptions) -> MonteCarloAssumptions:
    context = request.market_context
    return MonteCarloAssumptions(
        underwriting=underwriting,
        variables=tuple(
            SimulationVariable(
                key=item.key,
                confidence_level=item.confidence_level,
                confidence_percentage=item.confidence_percentage,
                minimum=item.minimum,
                maximum=item.maximum,
            )
            for item in request.variables
        ),
        iterations=request.iterations,
        seed=request.seed,
        target_levered_irr=request.target_levered_irr,
        correlations=tuple(
            Correlation(item.first_key, item.second_key, item.coefficient)
            for item in request.correlations
        ),
        market_context=(
            MarketContext(
                property_type=context.property_type,
                value_bucket=context.value_bucket,
                source=context.source,
                source_as_of_date=context.source_as_of_date.isoformat(),
                observations=context.observations,
                period_start=context.period_start,
                period_end=context.period_end,
            )
            if context
            else None
        ),
    )


def _to_development_assumptions(request: DevelopmentRequest) -> DevelopmentAssumptions:
    return DevelopmentAssumptions(
        construction=ConstructionLoanAssumptions(**request.construction.model_dump()),
        operating=_to_operating_assumptions(request.operating),
        **request.model_dump(exclude={"construction", "operating"}),
    )


def _to_sensitivity_assumptions(
    request: SavedSensitivityRequest,
    underwriting: UnderwritingAssumptions,
) -> SensitivityAssumptions:
    return SensitivityAssumptions(
        underwriting=underwriting,
        target_levered_irr=request.target_levered_irr,
        minimum_dscr=request.minimum_dscr,
        minimum_purchase_price=request.minimum_purchase_price,
        maximum_purchase_price=request.maximum_purchase_price,
        price_tolerance=request.price_tolerance,
        max_iterations=request.max_iterations,
    )


def _stored_underwriting_assumptions(
    assumption_set: AssumptionSetRecord, purchase_price: Decimal | None = None
) -> UnderwritingAssumptions:
    """Revalidate persisted JSON before it reaches the calculation engine.

    ``purchase_price`` substitutes an analysis price (for example the solved
    maximum price) for the reference price stored with the immutable inputs.
    """
    underwriting = _to_underwriting_assumptions(UnderwritingRequest.model_validate(assumption_set.inputs))
    return underwriting if purchase_price is None else replace(underwriting, purchase_price=purchase_price)


def _require_deal(repository: Repository, deal_id: str) -> DealRecord:
    deal = repository.get_deal(deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="deal not found")
    return deal


def _require_assumption_set(repository: Repository, assumption_set_id: str) -> AssumptionSetRecord:
    assumptions = repository.get_assumption_set(assumption_set_id)
    if assumptions is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assumption set not found")
    return assumptions


def _serialize_deal(deal: DealRecord) -> dict[str, Any]:
    return _serialize({"id": deal.id, "name": deal.name, "created_at": deal.created_at, "updated_at": deal.updated_at})


def _serialize_assumption_set(assumptions: AssumptionSetRecord) -> dict[str, Any]:
    return _serialize(
        {
            "id": assumptions.id,
            "deal_id": assumptions.deal_id,
            "version": assumptions.version,
            "label": assumptions.label,
            "source": assumptions.source,
            "effective_date": assumptions.effective_date,
            "confidence_level": assumptions.confidence_level,
            "property_type": assumptions.property_type,
            "value_bucket": assumptions.value_bucket,
            "underwriting": assumptions.inputs,
            "created_at": assumptions.created_at,
        }
    )


def _serialize_run(run: CalculationRunRecord) -> dict[str, Any]:
    return _serialize(
        {
            "id": run.id,
            "assumption_set_id": run.assumption_set_id,
            "calculation_type": run.calculation_type,
            "request": run.request,
            "engine_version": run.engine_version,
            "status": run.status,
            "error_message": run.error_message,
            "created_at": run.created_at,
            "result": run.result.payload if run.result else None,
        }
    )


def _serialize(value: Any) -> Any:
    """Return JSON-safe financial values without converting Decimal to float."""
    if isinstance(value, Decimal):
        return str(value)
    if is_dataclass(value):
        return {field.name: _serialize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, (tuple, list)):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


static_directory = Path(__file__).resolve().parents[1] / "static"
if static_directory.is_dir():
    app.mount("/", StaticFiles(directory=static_directory, html=True), name="frontend")


def run() -> None:
    """Run the local development server used by the project console script."""
    import uvicorn

    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8000)
