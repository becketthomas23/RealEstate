"""Store optional property, rent-roll, and expense detail with each assumption version."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261022_03"
down_revision: Union[str, Sequence[str], None] = "20261020_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assumption_sets", sa.Column("supporting_detail", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("assumption_sets", "supporting_detail")
