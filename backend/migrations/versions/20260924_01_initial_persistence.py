"""Create the initial audit-history persistence tables."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260924_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assumption_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("deal_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("confidence_level", sa.String(length=20), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deal_id", "version", name="uq_assumption_set_deal_version"),
    )
    op.create_index("ix_assumption_sets_deal_id", "assumption_sets", ["deal_id"], unique=False)
    op.create_table(
        "calculation_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("assumption_set_id", sa.String(length=36), nullable=False),
        sa.Column("calculation_type", sa.String(length=40), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("engine_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assumption_set_id"], ["assumption_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calculation_runs_assumption_set_id", "calculation_runs", ["assumption_set_id"], unique=False)
    op.create_table(
        "calculation_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("calculation_run_id", sa.String(length=36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["calculation_run_id"], ["calculation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("calculation_run_id"),
    )


def downgrade() -> None:
    op.drop_table("calculation_results")
    op.drop_index("ix_calculation_runs_assumption_set_id", table_name="calculation_runs")
    op.drop_table("calculation_runs")
    op.drop_index("ix_assumption_sets_deal_id", table_name="assumption_sets")
    op.drop_table("assumption_sets")
    op.drop_table("deals")
