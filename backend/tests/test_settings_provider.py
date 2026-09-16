"""
Tests for LLM provider settings:
- any authenticated role (analyst included) can save an API key (regression: was 403)
- POST /settings/test tests the submitted config (form), not only the saved DB row,
  and returns the resolved config (provider/model/base_url)
- POST /settings/detect determines the provider from an API key / Base URL
"""
from types import SimpleNamespace

import pytest


# ─── API-ключ сохраняется любым пользователем (analyst больше не получает 403) ──

@pytest.mark.asyncio
async def test_analyst_can_save_and_read_provider_api_key(client, auth_headers):
    resp = await client.post("/settings/providers", headers=auth_headers, json={
        "provider": "openai", "api_key": "sk-saved-by-analyst-9999",
        "model": "gpt-4o", "base_url": "", "temperature": 0.2,
        "max_tokens": 4096, "route": "", "is_active": False,
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["api_key_masked"].endswith("9999")

    lst = await client.get("/settings/providers", headers=auth_headers)
    assert lst.status_code == 200, lst.text
    rows = {p["provider"]: p for p in lst.json()}
    assert rows["openai"]["api_key_masked"].endswith("9999")
    assert rows["openai"]["model"] == "gpt-4o"


# ─── Тест соединения использует введённый (ещё не сохранённый) ключ и конфигурацию ──

@pytest.mark.asyncio
async def test_settings_test_uses_submitted_key_and_returns_config(client, auth_headers, monkeypatch):
    captured: dict = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured["create_kwargs"] = kwargs
            return SimpleNamespace(
                usage=None,
                choices=[SimpleNamespace(message=SimpleNamespace(content="OK от теста"))],
            )

    class FakeChat:
        completions = FakeCompletions()

    class FakeAsyncOpenAI:
        def __init__(self, api_key=None, base_url=None, **kw):
            captured["api_key"] = api_key
            captured["base_url"] = base_url

        @property
        def chat(self):
            return FakeChat()

    monkeypatch.setattr("openai.AsyncOpenAI", FakeAsyncOpenAI)

    resp = await client.post("/settings/test", headers=auth_headers, json={
        "provider": "openai",
        "api_key": "sk-correct-key-1234",
        "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "route": "",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    assert "OK" in data["response"]
    # именно тот ключ, что ввели в форму (не из БД)
    assert captured["api_key"] == "sk-correct-key-1234"
    assert captured["base_url"] == "https://api.openai.com/v1"
    assert captured["create_kwargs"]["model"] == "gpt-4o-mini"
    # вернулась итоговая конфигурация для UI
    assert data["config"]["provider"] == "openai"
    assert data["config"]["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_settings_test_400_without_key_for_cloud_provider(client, auth_headers, monkeypatch):
    # Провайдеру с ключом, но без ключа в форме и в БД — понятная ошибка 400.
    # Сначала сохраним настройку без ключа, чтобы в БД ключа не было.
    await client.post("/settings/providers", headers=auth_headers, json={
        "provider": "anthropic", "api_key": "", "model": "claude-sonnet-4-20250514",
        "base_url": "", "temperature": 0.2, "max_tokens": 4096, "route": "", "is_active": False,
    })
    resp = await client.post("/settings/test", headers=auth_headers, json={
        "provider": "anthropic", "api_key": "", "model": "", "base_url": "", "route": "",
    })
    assert resp.status_code == 400
    assert "API key" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_settings_test_ollama_requires_no_key(client, admin_auth_headers, monkeypatch):
    async def _fake_get(url):
        return SimpleNamespace(
            status_code=501,
            json=lambda: {},
        )

    fake_hc = SimpleNamespace(get=_fake_get, __aenter__=SimpleNamespace(__aexit__=(lambda *a: None)))

    async def _fake_client():
        return fake_hc

    monkeypatch.setattr("app.api.routers.settings.httpx.AsyncClient", _fake_client)

    resp = await client.post("/settings/test", headers=admin_auth_headers, json={
        "provider": "ollama", "api_key": "", "model": "qwen2.5:14b-instruct",
        "base_url": "http://localhost:11434/v1", "route": "",
    })
    assert resp.status_code == 200
    data = resp.json()
    # не 500: недоступный сервис → аккуратный {status: error}
    assert data["status"] == "error"
    assert data["config"]["is_local"] is True


# ─── Детекция провайдера по ключу / Base URL ──────────────────────────────────

@pytest.mark.asyncio
async def test_detect_provider_by_key_prefix(client, auth_headers):
    cases = [
        ({"api_key": "sk-ant-abcdef123456"}, "anthropic", "high"),
        ({"api_key": "sk-or-v1-abc123"}, "openrouter", "high"),
        ({"api_key": "sk-hello123", "base_url": "https://api.proxyapi.ru/openai/v1"}, "proxyapi", "high"),
        ({"api_key": "sk-hello123", "base_url": "https://api.openai.com/v1"}, "openai", "high"),
    ]
    for payload, expected, conf in cases:
        resp = await client.post("/settings/detect", headers=auth_headers, json=payload)
        assert resp.status_code == 200, resp.text
        d = resp.json()
        assert d["provider"] == expected, f"payload={payload}"
        assert d["confidence"] == conf
        assert expected in d["candidates"]
        assert d["default_model"]  # подсказка для пользователя


@pytest.mark.asyncio
async def test_detect_provider_ambiguous_sk(client, auth_headers):
    resp = await client.post("/settings/detect", headers=auth_headers, json={"api_key": "sk-xyz"})
    assert resp.status_code == 200
    d = resp.json()
    assert d["provider"] is None
    assert d["confidence"] == "medium"
    assert "openai" in d["candidates"] and "proxyapi" in d["candidates"]


@pytest.mark.asyncio
async def test_detect_provider_empty_key_suggests_ollama_or_none(client, auth_headers):
    resp = await client.post("/settings/detect", headers=auth_headers, json={"api_key": ""})
    assert resp.status_code == 200
    d = resp.json()
    assert d["provider"] is None

    resp2 = await client.post("/settings/detect", headers=auth_headers,
                              json={"api_key": "", "base_url": "http://localhost:11434/v1"})
    assert resp2.json()["provider"] == "ollama"
    assert resp2.json()["is_local"] is True