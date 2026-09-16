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
from app.services import llm_client


# ── Session-wide event loop ───────────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


# ── Auto-create DB tables + seed users once before any test runs ──────────────
@pytest.fixture(scope="session", autouse=True)
def create_db_tables():
    """Synchronously bootstrap async table creation and default users.

    Test DB is wiped before every session: several tests assert exact counts
    (e.g. total_runs == 1, actual usage == 1.0) and duplicate registrations are
    rejected, so a leftover `data/test_api.db` from a previous run made the suite
    order/history-dependent and repeated runs failed.
    """
    async def _setup():
        import re as _re
        from app.database import DATABASE_URL as _url
        m = _re.search(r"sqlite\+aiosqlite:///(.+)", _url)
        if m:
            db_file = os.path.abspath(m.group(1).lstrip("/"))
            if os.path.exists(db_file):
                os.remove(db_file)
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


# ── Admin auth headers — для эндпоинтов, закрытых require_admin (например /seed/*);
# настройки провайдеров (/settings/*) теперь доступны любому аутентифицированному
# пользователю (admin|analyst|architect).
@pytest_asyncio.fixture(scope="session")
async def admin_auth_headers(client):
    resp = await client.post(
        "/auth/login", data={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── LLM mock (autouse) — мокает call_llm для всех тестов по умолчанию ────────
# Реальный LLM (Ollama) медленный на CPU (3-5 мин на запрос). Unit-тесты не должны
# зависеть от скорости/доступности LLM. Тесты, которым нужен реальный LLM, помечаются
# маркером @pytest.mark.llm_real и используют фикстуру real_llm.
import json as _json

@pytest.fixture(autouse=True)
def mock_llm(request, monkeypatch):
    """Мокает call_llm для всех тестов, кроме помеченных @pytest.mark.llm_real."""
    if "llm_real" in request.keywords:
        yield  # реальный LLM
        return

    # llm_internal: тесты внутренней логики call_llm (конфиг, ключи, retry) — без мока
    if "llm_internal" in request.keywords:
        yield
        return

    _call_llm = llm_client.call_llm

    # llm_fail: мок бросает исключение (тестируем fallback-пути)
    _should_fail = "llm_fail" in request.keywords

    async def _fake_call_llm(prompt: str, system: str = "") -> str:
        """Возвращает минимальный валидный JSON, достаточный для большинства сервисов.
        Если тест помечен @pytest.mark.llm_fail — бросает RuntimeError (имитация ошибки LLM)."""
        if _should_fail:
            raise RuntimeError("LLM unavailable (mocked failure)")

        # Диаграммы: generate_all_diagrams ожидает JSON с полями диаграмм
        if "диаграмм" in prompt.lower() or "diagram" in prompt.lower() or "C4" in prompt:
            return _json.dumps({
                "c4_context": "@startuml\ntitle Context\n@enduml",
                "c4_container": "@startuml\ntitle Container\n@enduml",
                "c4_component": "@startuml\ntitle Component\n@enduml",
                "use_case": "@startuml\n:left to right direction\n:User: as U\nrectangle System {\n  usecase UC1\n}\nU --> UC1\n@enduml",
                "sequence": "@startuml\nactor User\nUser -> System: request\nSystem --> User: response\n@enduml",
                "class_diagram": "@startuml\nclass User {\n  name\n}\nclass Order {\n  id\n}\nUser --> Order\n@enduml",
                "erd": "@startuml\nentity User {\n  id : INTEGER\n  name : TEXT\n}\nentity Order {\n  id : INTEGER\n  user_id : INTEGER\n}\nUser ||--o{ Order\n@enduml",
            })
        # Review / general: минимальный JSON
        return _json.dumps({"status": "ok", "confidence": "low", "needs_review": True})

    monkeypatch.setattr("app.services.llm_client.call_llm", _fake_call_llm)
    # Также мокаем импорты call_llm в конкретных модулях
    for mod_name in ("app.services.diagram_engine", "app.services.ai_reviewer",
                     "app.services.rag_engine", "app.services.architecture_engine",
                     "app.services.doc_generator"):
        try:
            mod = __import__(mod_name, fromlist=["call_llm"])
            if hasattr(mod, "call_llm"):
                monkeypatch.setattr(f"{mod_name}.call_llm", _fake_call_llm)
        except Exception:
            pass
    yield

    # Восстанавливаем (monkeypatch делает это автоматически, но для llm_client явно)
    monkeypatch.setattr("app.services.llm_client.call_llm", _call_llm)
