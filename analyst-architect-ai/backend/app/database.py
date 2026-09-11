import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/analyst_architect_ai.db")

if DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

_ASYNC_ARGS = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_ASYNC_ARGS)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Ensure all tables exist. Prefers Alembic, falls back to sync create_all."""
    from app.models import (document, review, snippet, qa_run, audit_run,
        memory_item, decision, risk_catalog, project_lesson,
        architecture_review, api_spec, adr_record, diagram_artifact, diagram_version,
        documentation_standard, requirements_document,
        provider_settings, user, build_project, task_estimate,
        economic_estimate, economic_actual, batch_review, batch_review_item)

    # Bugfix (pre-existing, not part of Фаза 1): this used to hardcode
    # "data/analyst_architect_ai.db" regardless of DATABASE_URL, so alembic migrated a
    # DIFFERENT sqlite file than the one AsyncSessionLocal actually queries whenever
    # DATABASE_URL was overridden (e.g. tests/conftest.py uses .../test_api.db) —
    # tables were created in the wrong file and every DB-touching test/request failed
    # with "no such table". Now derived from the same DATABASE_URL as the async engine.
    sync_url = DATABASE_URL.replace("sqlite+aiosqlite:///", "sqlite:///", 1).replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )
    from sqlalchemy import create_engine as _sync_engine
    sync_connect_args = {"check_same_thread": False} if "sqlite" in sync_url else {}
    sync_engine = _sync_engine(sync_url, connect_args=sync_connect_args)

    if "sqlite" in sync_url:
        # Ensure the parent directory (e.g. ./data) exists before sqlite tries to create the file
        db_path = sync_url.replace("sqlite:///", "", 1)
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    used_alembic = False
    # Try Alembic first
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(alembic_cfg, "head")
        used_alembic = True
    except Exception:
        # Fallback: create_all (safe for local dev)
        Base.metadata.create_all(sync_engine)

    sync_engine.dispose()

    if not used_alembic:
        # Эпик B1: create_all не выполняет data-миграции (bulk_insert из 0003), поэтому
        # досеиваем справочник стандартов вручную для сценария "чистый create_all".
        from app.services.standards_seed import seed_default_standards
        from app.database import AsyncSessionLocal as _Session
        async with _Session() as db:
            await seed_default_standards(db)
