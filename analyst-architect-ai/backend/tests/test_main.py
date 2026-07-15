"""
pytest tests for AnalystGuru backend.
Run: pytest tests/ -v
"""
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# We test without LLM calls by mocking the services
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.services.ai_reviewer import run_ai_review, safe_fallback_review, _is_too_vague
from app.services.rag_engine import split_into_snippets, _keyword_score
from app.schemas import ReviewSchema, AnswerWithSourcesSchema


# ─── Unit tests: AI Reviewer ─────────────────────────────────────────────────

class TestAIReviewerLogic:
    def test_too_vague_detection_short(self):
        assert _is_too_vague("Сделать сайт.") is True

    def test_too_vague_detection_ok(self):
        long_text = "Нужна система авторизации с OAuth2, ролями администратор и пользователь, логированием всех действий."
        assert _is_too_vague(long_text) is False

    def test_safe_fallback_returns_needs_review(self):
        result = safe_fallback_review("INVALID_JSON", "test reason")
        assert result.needs_review is True
        assert result.confidence == "low"
        assert len(result.questions_to_client) >= 1

    def test_review_schema_serialization(self):
        schema = ReviewSchema(
            summary="Test summary",
            confidence="high",
            needs_review=False,
        )
        data = schema.model_dump()
        assert data["summary"] == "Test summary"
        assert data["needs_review"] is False

    def test_fallback_has_error_risk(self):
        result = safe_fallback_review("INVALID_JSON")
        assert len(result.risks) >= 1
        assert result.risks[0].severity in ("high", "medium", "low")


# ─── Unit tests: RAG Engine ──────────────────────────────────────────────────

class TestRAGEngine:
    def test_split_into_snippets_basic(self):
        text = "First paragraph with enough content here.\n\nSecond paragraph with more text here to test splitting."
        chunks = split_into_snippets(text)
        assert len(chunks) >= 1

    def test_split_into_snippets_long(self):
        # Long paragraph should be split
        long_text = " ".join(["word"] * 200)
        chunks = split_into_snippets(long_text, max_len=100)
        assert len(chunks) >= 2

    def test_keyword_score_perfect(self):
        score = _keyword_score("авторизация пользователь", "авторизация пользователь система")
        assert score == 1.0

    def test_keyword_score_partial(self):
        score = _keyword_score("авторизация пароль", "авторизация система")
        assert 0 < score < 1.0

    def test_keyword_score_empty(self):
        score = _keyword_score("", "some text")
        assert score == 0.0


# ─── Integration tests: API ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="module")
async def client():
    """Async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture(scope="module")
async def auth_headers(client):
    """Log in as the default analyst user and return Authorization headers."""
    # Ensure default users exist (in case this module runs standalone)
    from app.database import AsyncSessionLocal
    from app.services.auth_service import seed_default_users
    async with AsyncSessionLocal() as db:
        await seed_default_users(db)

    resp = await client.post(
        "/auth/login", data={"username": "analyst", "password": "analyst123"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_document(client, auth_headers):
    resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Test Document",
        "text": "Нужна форма заявки для клиентов с полями имя, телефон, email. Авторизация через логин/пароль.",
        "doc_type": "tz",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["title"] == "Test Document"
    return data["id"]


@pytest.mark.asyncio
async def test_list_documents(client, auth_headers):
    resp = await client.get("/documents", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_document_validation_too_short(client, auth_headers):
    resp = await client.post("/documents", headers=auth_headers, json={
        "title": "T",
        "text": "short",  # less than 10 chars min
        "doc_type": "tz",
    })
    assert resp.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_add_kb_document(client, auth_headers):
    resp = await client.post("/kb/documents", headers=auth_headers, json={
        "title": "Тест KB",
        "text": "Это тестовый документ базы знаний. SLA на ответы: 2 часа. Code review обязателен.",
        "doc_type": "kb_article",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["doc_type"] == "kb_article"


@pytest.mark.asyncio
async def test_list_kb_documents(client, auth_headers):
    resp = await client.get("/kb/documents", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_audit_endpoint(client, auth_headers):
    resp = await client.get("/audit", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_audit_stats(client, auth_headers):
    resp = await client.get("/audit/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "errors" in data
    assert "needs_review" in data


@pytest.mark.asyncio
async def test_memory_store(client, auth_headers):
    resp = await client.post("/memory/store", headers=auth_headers, json={
        "memory_type": "risk",
        "content": "Интеграция с внешним API может быть нестабильной при высокой нагрузке",
        "tags": ["api", "risk", "integration"],
        "project_name": "test-project",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["memory_type"] == "risk"


@pytest.mark.asyncio
async def test_memory_recent(client, auth_headers):
    resp = await client.get("/memory/recent", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_memory_search(client, auth_headers):
    resp = await client.post("/memory/search", headers=auth_headers, json={
        "query": "API риск интеграция",
        "limit": 5,
    })
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_business_endpoints_require_auth(client):
    """Business endpoints must reject requests without a valid JWT."""
    for path in ["/documents", "/audit", "/memory/recent", "/kb/documents"]:
        resp = await client.get(path)
        assert resp.status_code == 401, f"{path} should require auth, got {resp.status_code}"


# ─── Тест 10 ТЗ: needs_review logic ─────────────────────────────────────────

class TestNeedsReviewLogic:
    """Test that needs_review is correctly set based on input quality."""

    @pytest.mark.asyncio
    async def test_vague_spec_triggers_needs_review(self):
        """Spec #7: 'Сделать сайт.' should return needs_review=true."""
        from app.services.ai_reviewer import run_ai_review
        result = await run_ai_review("Сделать сайт.")
        assert result.needs_review is True
        assert len(result.questions_to_client) >= 3

    @pytest.mark.asyncio
    async def test_very_short_spec_triggers_needs_review(self):
        """Spec #8: 'Прилож.' should return needs_review=true."""
        result = await run_ai_review("Прилож.")
        assert result.needs_review is True
        assert result.confidence == "low"

    def test_safe_fallback_always_needs_review(self):
        """safe_fallback_review must always set needs_review=true."""
        for error_code in ["INVALID_JSON", "TOO_VAGUE_INPUT", "CONTRADICTORY_INPUT", "LLM_ERROR"]:
            result = safe_fallback_review(error_code)
            assert result.needs_review is True, f"Failed for error code: {error_code}"
            assert result.confidence == "low"


# ─── Reasoning modes (CoT / ReAct) — merged from MatveiV/Analyst-Guru ───────

class TestReasoningModes:
    def test_direct_mode_is_shortest_prompt(self):
        from app.services.ai_reviewer import _system_prompt_for_mode
        direct = _system_prompt_for_mode("direct")
        cot = _system_prompt_for_mode("cot")
        react = _system_prompt_for_mode("react")
        assert len(direct) < len(cot)
        assert len(direct) < len(react)

    def test_cot_prompt_requests_thinking_block(self):
        from app.services.ai_reviewer import _system_prompt_for_mode
        cot = _system_prompt_for_mode("cot")
        assert "<thinking>" in cot

    def test_react_prompt_requests_reasoning_block(self):
        from app.services.ai_reviewer import _system_prompt_for_mode
        react = _system_prompt_for_mode("react")
        assert "<reasoning>" in react
        assert "Thought" in react

    def test_strip_reasoning_removes_thinking_block(self):
        from app.services.ai_reviewer import _strip_reasoning_blocks
        raw = '<thinking>internal notes</thinking>{"summary": "ok"}'
        assert _strip_reasoning_blocks(raw) == '{"summary": "ok"}'

    def test_strip_reasoning_removes_react_block(self):
        from app.services.ai_reviewer import _strip_reasoning_blocks
        raw = '<reasoning>Thought: x\nAction: y</reasoning>{"summary": "ok"}'
        assert _strip_reasoning_blocks(raw) == '{"summary": "ok"}'

    def test_strip_reasoning_is_noop_without_blocks(self):
        from app.services.ai_reviewer import _strip_reasoning_blocks
        raw = '{"summary": "no reasoning block here"}'
        assert _strip_reasoning_blocks(raw) == raw


@pytest.mark.asyncio
async def test_direct_review_accepts_reasoning_mode_param(client, auth_headers):
    """direct_review endpoint accepts and validates the reasoning_mode field."""
    resp = await client.post("/ai/review", headers=auth_headers, json={
        "text": "Сделать сайт.",
        "reasoning_mode": "cot",
    })
    assert resp.status_code == 200
    # Vague input short-circuits before any reasoning-mode LLM call, but the field must be accepted
    assert resp.json()["needs_review"] is True


@pytest.mark.asyncio
async def test_direct_review_rejects_invalid_reasoning_mode(client, auth_headers):
    resp = await client.post("/ai/review", headers=auth_headers, json={
        "text": "Валидный текст технического задания для проверки.",
        "reasoning_mode": "not_a_real_mode",
    })
    assert resp.status_code == 422
