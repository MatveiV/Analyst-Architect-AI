"""split_documents

Физически разделяет таблицу `documents` (Вариант 2 + Вариант 5 в одной таблице)
на две отдельные сущности согласно `fix-prompt-analyst-architect-ai.md` §3–§4:

- `spec_documents` — ТЗ / BRD / User Story / SRS / Markdown (Вариант 2, рецензируемые)
- `kb_documents`  — статьи базы знаний команды (Вариант 5, для RAG)
- `kb_snippets`   — фрагменты KB (только они индексируются RAG-движком)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": name},
    ).fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # Идемпотентность: если миграция уже применена (например, БД создана через
    # create_all() после того, как модели уже разделены), просто выходим.
    if _table_exists(conn, "spec_documents") and _table_exists(conn, "kb_documents"):
        return

    # В SQLite изменение FK-структуры требует отключения проверки ссылок на время
    # миграции — иначе DROP TABLE на `documents` упадёт из-за FK от reviews/etc.
    conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
    try:
        # ── 1. Создаём новые таблицы ────────────────────────────────────────
        op.create_table(
            "spec_documents",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            # doc_type остаётся внутри spec_documents — подтип ТЗ/BRD/.../markdown
            sa.Column("doc_type", sa.String(50), server_default="tz"),
            sa.Column("project_name", sa.String(200), nullable=True),
            sa.Column("default_requirements_standard", sa.String(30), nullable=True),
            sa.Column("default_diagram_standard", sa.String(30), nullable=True),
        )

        op.create_table(
            "kb_documents",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("project_name", sa.String(200), nullable=True),
            # provenance: откуда KB-документ (urs/srs/adr/diagrams/lesson/null)
            sa.Column("source_type", sa.String(30), nullable=True),
            sa.Column("source_id", sa.String(36), nullable=True),
        )

        op.create_table(
            "kb_snippets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("document_id", sa.String(36), nullable=False),
            sa.Column("snippet_text", sa.Text(), nullable=False),
            sa.Column("embedding", sa.LargeBinary(), nullable=True),
            sa.ForeignKeyConstraint(["document_id"], ["kb_documents.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_kb_snippets_document_id", "kb_snippets", ["document_id"])

        # ── 2. Переносим данные из старых таблиц (если они ещё есть) ─────────
        if _table_exists(conn, "documents"):
            # Спецификации — все doc_type, кроме kb_article
            conn.execute(sa.text(
                """
                INSERT INTO spec_documents
                    (id, created_at, title, text, doc_type, project_name,
                     default_requirements_standard, default_diagram_standard)
                SELECT id, created_at, title, text, doc_type, project_name,
                       default_requirements_standard, default_diagram_standard
                FROM documents
                WHERE doc_type != 'kb_article' OR doc_type IS NULL
                """
            ))
            # База знаний — только kb_article
            conn.execute(sa.text(
                """
                INSERT INTO kb_documents
                    (id, created_at, title, text, project_name, source_type, source_id)
                SELECT id, created_at, title, text, project_name, source_type, source_id
                FROM documents
                WHERE doc_type = 'kb_article'
                """
            ))

            # Snippets: KB-фрагменты уезжают в kb_snippets; не-KB (если такие есть
            # исторически) теряются — на момент написания миграции snippets
            # использовался только RAG'ом по KB, поэтому потерь быть не должно.
            if _table_exists(conn, "snippets"):
                conn.execute(sa.text(
                    """
                    INSERT INTO kb_snippets
                        (id, created_at, document_id, snippet_text, embedding)
                    SELECT s.id, s.created_at, s.document_id, s.snippet_text, s.embedding
                    FROM snippets s
                    JOIN kb_documents k ON k.id = s.document_id
                    """
                ))

        # ── 3. Удаляем старые таблицы ────────────────────────────────────────
        # Snippets — безопасно: всё уже в kb_snippets
        if _table_exists(conn, "snippets"):
            op.drop_table("snippets")

        # Documents — FK со стороны reviews/architecture_reviews/api_specs/
        # adr_records/diagram_artifacts/requirements_documents отключены
        # через PRAGMA foreign_keys=OFF, теперь дропаем.
        if _table_exists(conn, "documents"):
            op.drop_table("documents")

        # ── 4. Перепривязываем FK на spec_documents ─────────────────────────
        # SQLite не умеет менять FK in-place, поэтому пересоздаём таблицы
        # с нужной ссылкой. Делается через copy-out / drop / copy-in.

        def _rebind_fk(table_name: str, fk_col: str = "document_id") -> None:
            if not _table_exists(conn, table_name):
                return
            # получить текущую схему (кроме FK)
            cols = conn.execute(sa.text(
                "SELECT name, type, \"notnull\", dflt_value, pk FROM pragma_table_info(:t) ORDER BY cid"
            ), {"t": table_name}).fetchall()
            # собрать CREATE TABLE для новой таблицы
            col_defs = []
            for c in cols:
                name, ctype, notnull, dflt, pk = c
                if pk:
                    col_defs.append(f'"{name}" {ctype} PRIMARY KEY')
                else:
                    parts = [f'"{name}" {ctype}']
                    if notnull:
                        parts.append("NOT NULL")
                    if dflt is not None:
                        parts.append(f"DEFAULT {dflt}")
                    col_defs.append(" ".join(parts))
            col_defs.append(f'FOREIGN KEY ("{fk_col}") REFERENCES "spec_documents"(id) ON DELETE CASCADE')
            tmp = f"{table_name}__new_fk"
            conn.execute(sa.text(f'DROP TABLE IF EXISTS "{tmp}"'))
            conn.execute(sa.text(f'CREATE TABLE "{tmp}" ({", ".join(col_defs)})'))
            cols_csv = ", ".join(f'"{c[0]}"' for c in cols)
            conn.execute(sa.text(
                f'INSERT INTO "{tmp}" ({cols_csv}) SELECT {cols_csv} FROM "{table_name}"'
            ))
            op.drop_table(table_name)
            # SQLite не поддерживает rename до произвольного имени, если уже существует — ок, имя уникальное
            conn.execute(sa.text(f'ALTER TABLE "{tmp}" RENAME TO "{table_name}"'))

        for tbl in ("reviews", "architecture_reviews", "api_specs",
                    "adr_records", "diagram_artifacts", "requirements_documents"):
            _rebind_fk(tbl)

    finally:
        conn.execute(sa.text("PRAGMA foreign_keys=ON"))


def downgrade() -> None:
    """Обратная миграция: сливаем spec_documents + kb_documents обратно в documents
    и перепривязываем FK. Используется только для отката в dev; в prod после
    релиза лучше оставить данные в новых таблицах."""
    conn = op.get_bind()

    conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
    try:
        if _table_exists(conn, "documents"):
            # уже откатили
            return

        op.create_table(
            "documents",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("doc_type", sa.String(50), server_default="tz"),
            sa.Column("project_name", sa.String(200), nullable=True),
            sa.Column("default_requirements_standard", sa.String(30), nullable=True),
            sa.Column("default_diagram_standard", sa.String(30), nullable=True),
            sa.Column("source_type", sa.String(30), nullable=True),
            sa.Column("source_id", sa.String(36), nullable=True),
        )

        conn.execute(sa.text(
            """
            INSERT INTO documents
                (id, created_at, title, text, doc_type, project_name,
                 default_requirements_standard, default_diagram_standard,
                 source_type, source_id)
            SELECT id, created_at, title, text, doc_type, project_name,
                   default_requirements_standard, default_diagram_standard,
                   NULL, NULL
            FROM spec_documents
            """
        ))
        conn.execute(sa.text(
            """
            INSERT INTO documents
                (id, created_at, title, text, doc_type, project_name,
                 default_requirements_standard, default_diagram_standard,
                 source_type, source_id)
            SELECT id, created_at, title, text, 'kb_article', project_name,
                   NULL, NULL, source_type, source_id
            FROM kb_documents
            """
        ))

        if _table_exists(conn, "kb_snippets") and not _table_exists(conn, "snippets"):
            op.rename_table("kb_snippets", "snippets")

        # Перепривязать FK обратно к documents
        def _rebind_fk_docs(table_name: str, fk_col: str = "document_id") -> None:
            if not _table_exists(conn, table_name):
                return
            cols = conn.execute(sa.text(
                "SELECT name, type, \"notnull\", dflt_value, pk FROM pragma_table_info(:t) ORDER BY cid"
            ), {"t": table_name}).fetchall()
            col_defs = []
            for c in cols:
                name, ctype, notnull, dflt, pk = c
                if pk:
                    col_defs.append(f'"{name}" {ctype} PRIMARY KEY')
                else:
                    parts = [f'"{name}" {ctype}']
                    if notnull:
                        parts.append("NOT NULL")
                    if dflt is not None:
                        parts.append(f"DEFAULT {dflt}")
                    col_defs.append(" ".join(parts))
            col_defs.append(f'FOREIGN KEY ("{fk_col}") REFERENCES "documents"(id) ON DELETE CASCADE')
            tmp = f"{table_name}__old_fk"
            conn.execute(sa.text(f'DROP TABLE IF EXISTS "{tmp}"'))
            conn.execute(sa.text(f'CREATE TABLE "{tmp}" ({", ".join(col_defs)})'))
            cols_csv = ", ".join(f'"{c[0]}"' for c in cols)
            conn.execute(sa.text(
                f'INSERT INTO "{tmp}" ({cols_csv}) SELECT {cols_csv} FROM "{table_name}"'
            ))
            op.drop_table(table_name)
            conn.execute(sa.text(f'ALTER TABLE "{tmp}" RENAME TO "{table_name}"'))

        for tbl in ("reviews", "architecture_reviews", "api_specs",
                    "adr_records", "diagram_artifacts", "requirements_documents"):
            _rebind_fk_docs(tbl)

        op.drop_table("spec_documents")
        op.drop_table("kb_documents")

    finally:
        conn.execute(sa.text("PRAGMA foreign_keys=ON"))
