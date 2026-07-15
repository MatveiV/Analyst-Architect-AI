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
        architecture_review, api_spec, adr_record, diagram_artifact,
        provider_settings, user, build_project, task_estimate,
        economic_estimate, economic_actual)

    db_abs = str(Path(__file__).resolve().parents[1] / "data" / "analyst_architect_ai.db")
    from sqlalchemy import create_engine as _sync_engine
    sync_engine = _sync_engine(f"sqlite:///{db_abs}", connect_args={"check_same_thread": False})

    # Try Alembic first
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_abs}")
        command.upgrade(alembic_cfg, "head")
    except Exception:
        # Fallback: create_all (safe for local dev)
        Base.metadata.create_all(sync_engine)

    sync_engine.dispose()
