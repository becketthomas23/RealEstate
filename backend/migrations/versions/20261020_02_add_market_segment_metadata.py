"""Store immutable property-type and value-bucket context with assumptions."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261020_02"
down_revision: Union[str, Sequence[str], None] = "20260924_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assumption_sets",
        sa.Column("property_type", sa.String(length=100), nullable=False, server_default="Multifamily"),
    )
    op.add_column(
        "assumption_sets",
        sa.Column("value_bucket", sa.String(length=100), nullable=False, server_default="Custom"),
    )


def downgrade() -> None:
    op.drop_column("assumption_sets", "value_bucket")
    op.drop_column("assumption_sets", "property_type")
