"""Portable relational records for immutable assumptions and calculation history."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _new_id() -> str:
    return str(uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class DealRecord(Base):
    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
    assumption_sets: Mapped[list[AssumptionSetRecord]] = relationship(back_populates="deal", cascade="all, delete-orphan")


class AssumptionSetRecord(Base):
    __tablename__ = "assumption_sets"
    __table_args__ = (UniqueConstraint("deal_id", "version", name="uq_assumption_set_deal_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    deal_id: Mapped[str] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    deal: Mapped[DealRecord] = relationship(back_populates="assumption_sets")
    calculation_runs: Mapped[list[CalculationRunRecord]] = relationship(back_populates="assumption_set", cascade="all, delete-orphan")


class CalculationRunRecord(Base):
    __tablename__ = "calculation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    assumption_set_id: Mapped[str] = mapped_column(ForeignKey("assumption_sets.id", ondelete="CASCADE"), nullable=False, index=True)
    calculation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    assumption_set: Mapped[AssumptionSetRecord] = relationship(back_populates="calculation_runs")
    result: Mapped[CalculationResultRecord | None] = relationship(back_populates="calculation_run", cascade="all, delete-orphan", uselist=False)


class CalculationResultRecord(Base):
    __tablename__ = "calculation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    calculation_run_id: Mapped[str] = mapped_column(ForeignKey("calculation_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    calculation_run: Mapped[CalculationRunRecord] = relationship(back_populates="result")
