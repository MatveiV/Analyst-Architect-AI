"""usage economics + kb autoindex provenance (Фаза 3)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-19
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("audit_runs", sa.Column("input_tokens", sa.Integer(), nullable=True))
    op.add_column("audit_runs", sa.Column("output_tokens", sa.Integer(), nullable=True))
    op.add_column("audit_runs", sa.Column("estimated_cost_usd", sa.Float(), nullable=True))

    op.add_column("documents", sa.Column("source_type", sa.String(30), nullable=True))
    op.add_column("documents", sa.Column("source_id", sa.String(36), nullable=True))

    # "manual" | "actual_usage" — откуда взято llm_cost_monthly в этой оценке (Фаза 3)
    op.add_column(
        "economic_estimates",
        sa.Column("llm_cost_source", sa.String(20), nullable=False, server_default="manual"),
    )


def downgrade() -> None:
    op.drop_column("economic_estimates", "llm_cost_source")
    op.drop_column("documents", "source_id")
    op.drop_column("documents", "source_type")
    op.drop_column("audit_runs", "estimated_cost_usd")
    op.drop_column("audit_runs", "output_tokens")
    op.drop_column("audit_runs", "input_tokens")
