"""
conftest.py — sets DATABASE_URL before any app import, creates tables,
provides a session-scoped HTTPX client for integration tests.
"""
import asyncio
import os

# Must be set BEFORE any app module import
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test_api.db")
os.makedirs("data", exist_ok=True)

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.database import create_tables
from app.main import app


# ── Session-wide event loop ───────────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


# ── Auto-create DB tables + seed users once before any test runs ──────────────
@pytest.fixture(scope="session", autouse=True)
def create_db_tables():
    """Synchronously bootstrap async table creation and default users."""
    async def _setup():
        await create_tables()
        from app.database import AsyncSessionLocal
        from app.services.auth_service import seed_default_users
        async with AsyncSessionLocal() as db:
            await seed_default_users(db)

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_setup())
    loop.close()


# ── Shared HTTPX client ───────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ── Shared auth headers (logs in as the default `analyst` user) ──────────────
@pytest_asyncio.fixture(scope="session")
async def auth_headers(client):
    resp = await client.post(
        "/auth/login", data={"username": "analyst", "password": "analyst123"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Raw DB session, для тестов, вызывающих сервисный слой напрямую (Эпик C) ──
@pytest_asyncio.fixture
async def db_session():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


# ── Admin auth headers — для эндпоинтов, закрытых require_architect/require_admin
# (например /settings/providers) — обычного analyst-токена туда недостаточно (403).
@pytest_asyncio.fixture(scope="session")
async def admin_auth_headers(client):
    resp = await client.post(
        "/auth/login", data={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
