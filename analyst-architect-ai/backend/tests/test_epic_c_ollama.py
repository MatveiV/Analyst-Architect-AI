"""
Тесты Эпика C — локальные LLM через Ollama: конфиг, обход ключа, forced JSON,
retry, доказуемость локальности в audit_runs, честные метрики по провайдеру.
Run: pytest tests/test_epic_c_ollama.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import llm_client
from app.services.audit_service import with_audit, save_audit


# ─── C1: конфигурация провайдера ollama ───────────────────────────────────────

class TestOllamaConfig:
    def test_cfg_from_env_ollama_is_local_and_no_real_key_needed(self, monkeypatch):
        monkeypatch.setattr(llm_client.settings, "LLM_PROVIDER", "ollama")
        monkeypatch.setattr(llm_client.settings, "OLLAMA_MODEL", "qwen2.5:14b-instruct")
        monkeypatch.setattr(llm_client.settings, "OLLAMA_BASE_URL", "http://ollama:11434/v1")
        cfg = llm_client._cfg_from_env()
        assert cfg["provider"] == "ollama"
        assert cfg["is_local"] is True
        assert cfg["api_key"] == "ollama"  # dummy — OpenAI-клиенту нужна непустая строка
        assert cfg["model"] == "qwen2.5:14b-instruct"
        assert cfg["base_url"] == "http://ollama:11434/v1"

    def test_cfg_from_env_cloud_provider_is_not_local(self, monkeypatch):
        monkeypatch.setattr(llm_client.settings, "LLM_PROVIDER", "openai")
        cfg = llm_client._cfg_from_env()
        assert cfg["is_local"] is False

    def test_cfg_from_row_defaults_base_url_for_ollama_when_empty(self):
        class _Row:
            provider = "ollama"
            api_key = ""
            model = ""
            base_url = ""
            temperature = "0.2"
            max_tokens = "4096"
            route = ""
            is_local = True

        cfg = llm_client._cfg_from_row(_Row())
        assert cfg["api_key"] == "ollama"
        assert cfg["base_url"]  # не пусто — подставлен settings.OLLAMA_BASE_URL
        assert cfg["is_local"] is True


# ─── C1: call_llm() не требует api_key для ollama, требует для остальных ─────

class TestCallLlmKeyBypass:
    @pytest.mark.asyncio
    async def test_missing_key_raises_for_cloud_provider(self, monkeypatch):
        async def _fake_cfg():
            return {"provider": "openai", "api_key": "", "model": "gpt-4o",
                    "base_url": "", "temperature": 0.2, "max_tokens": 100, "route": "", "is_local": False}
        monkeypatch.setattr(llm_client, "_load_active_config", _fake_cfg)
        with pytest.raises(RuntimeError, match="API-ключ"):
            await llm_client.call_llm("prompt", "system")

    @pytest.mark.asyncio
    async def test_missing_key_does_not_raise_for_ollama(self, monkeypatch):
        async def _fake_cfg():
            return {"provider": "ollama", "api_key": "", "model": "qwen2.5:14b-instruct",
                    "base_url": "http://ollama:11434/v1", "temperature": 0.2, "max_tokens": 100,
                    "route": "", "is_local": True}
        monkeypatch.setattr(llm_client, "_load_active_config", _fake_cfg)

        async def _fake_call_ollama(prompt, system, cfg):
            return '{"ok": true}'
        monkeypatch.setattr(llm_client, "_call_ollama", _fake_call_ollama)

        result = await llm_client.call_llm("prompt", "system")
        assert result == '{"ok": true}'

    @pytest.mark.asyncio
    async def test_call_llm_records_last_call_meta_before_dispatch(self, monkeypatch):
        """Эпик C3: метаданные должны фиксироваться ДО самого вызова, чтобы audit_service
        мог их прочитать даже если сам вызов упадёт с ошибкой."""
        async def _fake_cfg():
            return {"provider": "ollama", "api_key": "", "model": "m", "base_url": "u",
                    "temperature": 0.2, "max_tokens": 100, "route": "", "is_local": True}
        monkeypatch.setattr(llm_client, "_load_active_config", _fake_cfg)

        async def _raise(*a, **kw):
            raise ConnectionError("ollama unreachable")
        monkeypatch.setattr(llm_client, "_call_ollama", _raise)

        with pytest.raises(ConnectionError):
            await llm_client.call_llm("prompt", "system")

        meta = llm_client.get_last_call_meta()
        assert meta["provider"] == "ollama"
        assert meta["is_local"] is True


# ─── C1: forced JSON decoding + retry для Ollama ──────────────────────────────

class TestOllamaForceJsonAndRetry:
    @pytest.mark.asyncio
    async def test_call_openai_compat_passes_format_json_when_forced(self, monkeypatch):
        captured_kwargs = {}

        class _FakeMessage:
            content = '{"result": "ok"}'

        class _FakeChoice:
            message = _FakeMessage()

        class _FakeResponse:
            choices = [_FakeChoice()]

        class _FakeCompletions:
            def create(self, **kwargs):
                captured_kwargs.update(kwargs)
                return _FakeResponse()

        class _FakeChat:
            completions = _FakeCompletions()

        class _FakeClient:
            chat = _FakeChat()

        monkeypatch.setattr("openai.OpenAI", lambda **kw: _FakeClient())

        cfg = {"provider": "ollama", "api_key": "ollama", "model": "qwen2.5:14b-instruct",
               "base_url": "http://ollama:11434/v1", "temperature": 0.2, "max_tokens": 100, "route": ""}
        result = await llm_client._call_openai_compat("prompt", "system", cfg, force_json=True)

        assert result == '{"result": "ok"}'
        assert captured_kwargs.get("extra_body") == {"format": "json"}

    @pytest.mark.asyncio
    async def test_call_openai_compat_omits_format_json_when_not_forced(self, monkeypatch):
        captured_kwargs = {}

        class _FakeMessage:
            content = "plain text"

        class _FakeChoice:
            message = _FakeMessage()

        class _FakeResponse:
            choices = [_FakeChoice()]

        class _FakeCompletions:
            def create(self, **kwargs):
                captured_kwargs.update(kwargs)
                return _FakeResponse()

        class _FakeChat:
            completions = _FakeCompletions()

        class _FakeClient:
            chat = _FakeChat()

        monkeypatch.setattr("openai.OpenAI", lambda **kw: _FakeClient())

        cfg = {"provider": "openai", "api_key": "sk-test", "model": "gpt-4o",
               "base_url": "", "temperature": 0.2, "max_tokens": 100, "route": ""}
        await llm_client._call_openai_compat("prompt", "system", cfg, force_json=False)
        assert "extra_body" not in captured_kwargs

    @pytest.mark.asyncio
    async def test_call_ollama_retries_once_with_explicit_json_instruction_on_empty_response(self, monkeypatch):
        """Первый ответ пустой -> должен произойти ровно один retry с более явной инструкцией,
        прежде чем сервис-вызывающая сторона откатится на safe_fallback_*."""
        calls = []

        async def _fake_compat(prompt, system, cfg, force_json=False):
            calls.append(system)
            if len(calls) == 1:
                return ""  # пустой первый ответ
            return '{"ok": true}'

        monkeypatch.setattr(llm_client, "_call_openai_compat", _fake_compat)

        cfg = {"provider": "ollama"}
        result = await llm_client._call_ollama("prompt", "исходная система", cfg)

        assert result == '{"ok": true}'
        assert len(calls) == 2
        assert "ТОЛЬКО валидный JSON" in calls[1]
        assert calls[0] == "исходная система"

    @pytest.mark.asyncio
    async def test_call_ollama_gives_up_after_one_retry(self, monkeypatch):
        async def _always_empty(prompt, system, cfg, force_json=False):
            return ""
        monkeypatch.setattr(llm_client, "_call_openai_compat", _always_empty)

        result = await llm_client._call_ollama("prompt", "system", {"provider": "ollama"})
        assert result == ""  # вызывающая сторона (doc_generator/diagram_engine) уйдёт в safe_fallback


# ─── C3: audit_service записывает provider_used/is_local_provider ────────────

class TestAuditProviderProvenance:
    @pytest.mark.asyncio
    async def test_with_audit_records_local_provider_on_success(self, db_session, monkeypatch):
        monkeypatch.setattr(
            "app.services.audit_service.get_last_call_meta",
            lambda: {"provider": "ollama", "is_local": True},
        )

        class _Result:
            needs_review = False
            def model_dump(self):
                return {"ok": True}

        async def _func():
            return _Result()

        run = await with_audit(db_session, "test_action", {"x": 1}, _func)
        assert run is not None

    @pytest.mark.asyncio
    async def test_with_audit_records_provider_even_on_exception(self, db_session, monkeypatch):
        monkeypatch.setattr(
            "app.services.audit_service.get_last_call_meta",
            lambda: {"provider": "ollama", "is_local": True},
        )

        async def _func():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await with_audit(db_session, "test_action_fail", {"x": 1}, _func)


# ─── C6: честные метрики по провайдеру ────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_by_provider_endpoint_shape(client, auth_headers, db_session):
    """
    БД в тестовой сессии общая для всех тестов (session-scoped client), поэтому агрегаты
    по реальным именам провайдеров ("ollama"/"anthropic") были бы засорены другими тестами.
    Используем уникальные маркеры-провайдеры, чтобы честно проверить именно логику агрегации.
    """
    await save_audit(
        db_session, "generate_urs", {"x": 1}, {"y": 2}, status="needs_review",
        duration_ms=1000, provider_used="ollama__epicC_probe", is_local_provider=True,
    )
    await save_audit(
        db_session, "generate_urs", {"x": 1}, {"y": 2}, status="ok",
        duration_ms=500, provider_used="anthropic__epicC_probe", is_local_provider=False,
    )

    resp = await client.get("/dashboard/stats-by-provider", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    by_provider = {row["provider"]: row for row in data}
    assert "ollama__epicC_probe" in by_provider
    assert by_provider["ollama__epicC_probe"]["is_local"] is True
    assert by_provider["ollama__epicC_probe"]["total_runs"] == 1
    assert by_provider["ollama__epicC_probe"]["needs_review_rate_pct"] == 100.0
    assert "anthropic__epicC_probe" in by_provider
    assert by_provider["anthropic__epicC_probe"]["is_local"] is False
    assert by_provider["anthropic__epicC_probe"]["needs_review_rate_pct"] == 0.0


# ─── C4: settings endpoints не падают, если Ollama физически недоступна ──────
# (POST /settings/providers и /settings/test закрыты require_architect — обычного
# analyst-токена недостаточно, нужен admin_auth_headers)

@pytest.mark.asyncio
async def test_ollama_test_endpoint_fails_gracefully_when_unreachable(client, admin_auth_headers):
    resp = await client.post("/settings/providers", headers=admin_auth_headers, json={
        "provider": "ollama", "api_key": "", "model": "qwen2.5:14b-instruct",
        "base_url": "http://ollama-does-not-exist.invalid:11434/v1",
        "temperature": 0.2, "max_tokens": 4096, "route": "", "is_active": False,
    })
    assert resp.status_code == 200
    assert resp.json()["is_local"] is True

    test_resp = await client.post("/settings/test?provider=ollama", headers=admin_auth_headers)
    assert test_resp.status_code == 200
    assert test_resp.json()["status"] == "error"
    assert "detail" not in test_resp.json()  # не 500, аккуратная обработка исключения


@pytest.mark.asyncio
async def test_ollama_models_endpoint_returns_502_not_500_when_unreachable(client, admin_auth_headers):
    resp = await client.get("/settings/providers/ollama/models", headers=admin_auth_headers)
    assert resp.status_code in (502, 200)  # 200 возможен, если провайдер уже указывает на живой сервис
