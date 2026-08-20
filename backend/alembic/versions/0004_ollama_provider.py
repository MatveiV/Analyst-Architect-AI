"""ollama / local provider provenance (Эпик C3)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "provider_settings",
        sa.Column("is_local", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("audit_runs", sa.Column("provider_used", sa.String(50), nullable=True))
    op.add_column(
        "audit_runs",
        sa.Column("is_local_provider", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("audit_runs", "is_local_provider")
    op.drop_column("audit_runs", "provider_used")
    op.drop_column("provider_settings", "is_local")
