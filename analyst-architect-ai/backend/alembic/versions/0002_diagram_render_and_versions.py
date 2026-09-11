"""diagram render storage + version history (Эпик A2-A3)

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("diagram_artifacts", sa.Column("render_svg", sa.Text(), nullable=True))
    op.add_column("diagram_artifacts", sa.Column("render_png", sa.LargeBinary(), nullable=True))
    op.add_column("diagram_artifacts", sa.Column("rendered_at", sa.DateTime(), nullable=True))
    op.add_column(
        "diagram_artifacts",
        sa.Column("render_status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.add_column("diagram_artifacts", sa.Column("render_error", sa.String(300), nullable=True))
    op.add_column("diagram_artifacts", sa.Column("standard_profile", sa.String(30), nullable=True))

    op.create_table(
        "diagram_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("diagram_artifact_id", sa.String(36), sa.ForeignKey("diagram_artifacts.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("notation", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("change_note", sa.String(300), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("diagram_versions")
    op.drop_column("diagram_artifacts", "standard_profile")
    op.drop_column("diagram_artifacts", "render_error")
    op.drop_column("diagram_artifacts", "render_status")
    op.drop_column("diagram_artifacts", "rendered_at")
    op.drop_column("diagram_artifacts", "render_png")
    op.drop_column("diagram_artifacts", "render_svg")
