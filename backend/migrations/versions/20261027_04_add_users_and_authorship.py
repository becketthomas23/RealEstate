"""Add user accounts and record who created deals and versions."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261027_04"
down_revision: Union[str, Sequence[str], None] = "20261022_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=300), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="analyst"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.add_column("deals", sa.Column("created_by", sa.String(length=320), nullable=True))
    op.add_column("assumption_sets", sa.Column("created_by", sa.String(length=320), nullable=True))


def downgrade() -> None:
    op.drop_column("assumption_sets", "created_by")
    op.drop_column("deals", "created_by")
    op.drop_table("users")
