"""standards profile: documentation_standards + requirements_documents (Эпик B1-B2)

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-17
"""
from datetime import datetime
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


SEED_STANDARDS = [
    dict(id="IEEE_830", name_ru="IEEE 830-1998 (SRS)", name_en="IEEE 830-1998 (SRS)",
         family="requirements",
         description="Классическая структура Software Requirements Specification."),
    dict(id="ISO_IEC_IEEE_29148", name_ru="ISO/IEC/IEEE 29148 (Requirements Engineering)",
         name_en="ISO/IEC/IEEE 29148 (Requirements Engineering)", family="requirements",
         description="Актуальный международный стандарт, преемник IEEE 830. Используется по умолчанию."),
    dict(id="GOST_19", name_ru="ГОСТ 19.201-78 (ТЗ на программу, ЕСПД)",
         name_en="GOST 19.201-78 (Software TOR, ESPD)", family="requirements",
         description="Российский стандарт ЕСПД для технического задания на программу."),
    dict(id="GOST_34", name_ru="ГОСТ 34.602-2020 (ТЗ на автоматизированную систему)",
         name_en="GOST 34.602-2020 (Automated system TOR)", family="requirements",
         description="Часто требуется банками и государственными заказчиками РФ."),
    dict(id="C4_MODEL", name_ru="C4-модель (Simon Brown)", name_en="C4 model (Simon Brown)",
         family="diagram",
         description="Context/Container/Component/Code — используется по умолчанию в проекте."),
    dict(id="UML_ISO_19505", name_ru="UML по ISO/IEC 19505", name_en="UML per ISO/IEC 19505",
         family="diagram",
         description="Use Case, Sequence, Class, State, Activity диаграммы."),
    dict(id="ISO_IEC_IEEE_42010", name_ru="ISO/IEC/IEEE 42010 (Architecture description)",
         name_en="ISO/IEC/IEEE 42010 (Architecture description)", family="diagram",
         description="Комплект видов архитектуры (viewpoints), привязанных к интересам стейкхолдеров."),
    dict(id="GOST_19_701", name_ru="ГОСТ 19.701-90 (Схемы алгоритмов, программ, данных)",
         name_en="GOST 19.701-90 (Program/data flowcharts)", family="diagram",
         description="Приближённая генерация: needs_review=true по умолчанию, требуется ручная сверка обозначений."),
    dict(id="IEC_61082", name_ru="IEC 61082 (Оформление технической документации)",
         name_en="IEC 61082 (Preparation of technical documents)", family="diagram",
         description="В первую очередь про электротехническую документацию; для чисто ПО-систем "
                     "применим ограниченно — актуален для проектов на стыке с АСУ ТП/встраиваемыми "
                     "системами. needs_review=true по умолчанию."),
]

documentation_standards_table = sa.table(
    "documentation_standards",
    sa.column("id", sa.String),
    sa.column("name_ru", sa.String),
    sa.column("name_en", sa.String),
    sa.column("family", sa.String),
    sa.column("description", sa.Text),
    sa.column("is_active", sa.Boolean),
)


def upgrade() -> None:
    op.create_table(
        "documentation_standards",
        sa.Column("id", sa.String(30), primary_key=True),
        sa.Column("name_ru", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("family", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.bulk_insert(
        documentation_standards_table,
        [{**row, "is_active": True} for row in SEED_STANDARDS],
    )

    op.add_column("documents", sa.Column("default_requirements_standard", sa.String(30), nullable=True))
    op.add_column("documents", sa.Column("default_diagram_standard", sa.String(30), nullable=True))
    op.add_column("reviews", sa.Column("standard_profile", sa.String(30), nullable=True))
    op.add_column("adr_records", sa.Column("standard_profile", sa.String(30), nullable=True))
    op.add_column("api_specs", sa.Column("standard_profile", sa.String(30), nullable=True))

    op.create_table(
        "requirements_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("doc_kind", sa.String(10), nullable=False),
        sa.Column("standard_profile", sa.String(30), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("requirements_documents")
    op.drop_column("api_specs", "standard_profile")
    op.drop_column("adr_records", "standard_profile")
    op.drop_column("reviews", "standard_profile")
    op.drop_column("documents", "default_diagram_standard")
    op.drop_column("documents", "default_requirements_standard")
    op.drop_table("documentation_standards")
