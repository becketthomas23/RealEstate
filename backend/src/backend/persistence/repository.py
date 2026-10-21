"""Small transaction-oriented repository for the underwriting API."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from .models import AssumptionSetRecord, CalculationResultRecord, CalculationRunRecord, DealRecord


ENGINE_VERSION = "0.1.0"


class Repository:
    """Keep storage concerns out of calculation engines and HTTP handlers."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_deal(self, name: str) -> DealRecord:
        deal = DealRecord(name=name)
        self.session.add(deal)
        self.session.commit()
        self.session.refresh(deal)
        return deal

    def list_deals(self) -> list[DealRecord]:
        return list(self.session.scalars(select(DealRecord).order_by(DealRecord.updated_at.desc(), DealRecord.created_at.desc())))

    def get_deal(self, deal_id: str) -> DealRecord | None:
        return self.session.get(DealRecord, deal_id)

    def create_assumption_set(
        self,
        *,
        deal: DealRecord,
        label: str,
        source: str | None,
        effective_date: date,
        confidence_level: str,
        property_type: str,
        value_bucket: str,
        inputs: dict[str, Any],
    ) -> AssumptionSetRecord:
        latest_version = self.session.scalar(
            select(func.max(AssumptionSetRecord.version)).where(AssumptionSetRecord.deal_id == deal.id)
        )
        assumptions = AssumptionSetRecord(
            deal_id=deal.id,
            version=(latest_version or 0) + 1,
            label=label,
            source=source,
            effective_date=effective_date,
            confidence_level=confidence_level,
            property_type=property_type,
            value_bucket=value_bucket,
            inputs=inputs,
        )
        deal.updated_at = datetime.now(timezone.utc)
        self.session.add(assumptions)
        self.session.commit()
        self.session.refresh(assumptions)
        return assumptions

    def get_assumption_set(self, assumption_set_id: str) -> AssumptionSetRecord | None:
        return self.session.get(AssumptionSetRecord, assumption_set_id)

    def list_assumption_sets(self, deal_id: str) -> list[AssumptionSetRecord]:
        return list(
            self.session.scalars(
                select(AssumptionSetRecord)
                .where(AssumptionSetRecord.deal_id == deal_id)
                .order_by(AssumptionSetRecord.version.desc())
            )
        )

    def create_completed_run(
        self,
        *,
        assumption_set: AssumptionSetRecord,
        calculation_type: str,
        request: dict[str, Any],
        result: dict[str, Any],
    ) -> CalculationRunRecord:
        run = CalculationRunRecord(
            assumption_set_id=assumption_set.id,
            calculation_type=calculation_type,
            request=request,
            engine_version=ENGINE_VERSION,
            status="completed",
        )
        run.result = CalculationResultRecord(payload=result)
        self.session.add(run)
        self.session.commit()
        return self.get_run(run.id)  # type: ignore[return-value]

    def get_run(self, run_id: str) -> CalculationRunRecord | None:
        statement = select(CalculationRunRecord).options(joinedload(CalculationRunRecord.result)).where(CalculationRunRecord.id == run_id)
        return self.session.scalar(statement)

    def list_runs(self, assumption_set_id: str) -> list[CalculationRunRecord]:
        statement = (
            select(CalculationRunRecord)
            .options(joinedload(CalculationRunRecord.result))
            .where(CalculationRunRecord.assumption_set_id == assumption_set_id)
            .order_by(CalculationRunRecord.created_at.desc())
        )
        return list(self.session.scalars(statement))
