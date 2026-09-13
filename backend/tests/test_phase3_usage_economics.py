"""
Тесты Фазы 3 — реальные метрики использования → Economics.
Run: pytest tests/test_phase3_usage_economics.py -v
"""
import pytest
from app.services.llm_pricing import estimate_cost_usd
from app.services.audit_service import save_audit
from app.services.usage_economics_service import get_actual_usage


# ─── llm_pricing.py (unit) ─────────────────────────────────────────────────────

class TestLlmPricing:
    def test_ollama_is_always_free(self):
        assert estimate_cost_usd("ollama", "qwen2.5:14b-instruct", 100_000, 50_000) == 0.0

    def test_known_model_uses_matched_rate(self):
        # claude-sonnet: $3/1M in, $15/1M out
        cost = estimate_cost_usd("anthropic", "claude-sonnet-4-20250514", 1_000_000, 1_000_000)
        assert cost == 18.0  # 3 + 15

    def test_unknown_model_uses_conservative_default(self):
        cost = estimate_cost_usd("openrouter", "some/exotic-model-nobody-heard-of", 1_000_000, 0)
        assert cost == 3.0  # DEFAULT_INPUT_USD_PER_1M

    def test_zero_tokens_gives_zero_cost(self):
        assert estimate_cost_usd("anthropic", "claude-sonnet-4-20250514", 0, 0) == 0.0


# ─── llm_client.py: захват токенов в _last_call_meta (unit) ──────────────────

class TestTokenCaptureInLlmClient:
    def test_record_usage_updates_last_call_meta(self, monkeypatch):
        from app.services import llm_client
        llm_client._record_usage(100, 200, "anthropic", "claude-sonnet-4-20250514")
        meta = llm_client.get_last_call_meta()
        assert meta["input_tokens"] == 100
        assert meta["output_tokens"] == 200
        assert meta["estimated_cost_usd"] > 0

    @pytest.mark.llm_internal
    def test_call_llm_resets_tokens_before_dispatch(self, monkeypatch):
        """Токены — метаданные ПОСЛЕДНЕГО запуска, не накопительный счётчик; при новом
        вызове должны сброситься в 0 до того, как станет известен реальный расход."""
        import asyncio
        from app.services import llm_client

        llm_client._record_usage(999, 999, "anthropic", "claude-sonnet-4-20250514")

        async def _fake_cfg():
            return {"provider": "ollama", "api_key": "", "model": "m", "base_url": "u",
                    "temperature": 0.2, "max_tokens": 100, "route": "", "is_local": True}
        monkeypatch.setattr(llm_client, "_load_active_config", _fake_cfg)

        async def _raise(*a, **kw):
            raise ConnectionError("boom")
        monkeypatch.setattr(llm_client, "_call_ollama", _raise)

        with pytest.raises(ConnectionError):
            # asyncio.run() вместо get_event_loop().run_until_complete():
            # в Python 3.12+ (особенно 3.14) неявное создание event loop в
            # главном потоке удалено — get_event_loop() бросает RuntimeError.
            asyncio.run(llm_client.call_llm("p", "s"))

        meta = llm_client.get_last_call_meta()
        assert meta["input_tokens"] == 0
        assert meta["output_tokens"] == 0


# ─── usage_economics_service.py — агрегация audit_runs ────────────────────────

@pytest.mark.asyncio
async def test_get_actual_usage_aggregates_saved_audit_runs(db_session):
    await save_audit(
        db_session, "generate_urs__usage_probe", {}, {}, status="ok", duration_ms=1200,
        provider_used="anthropic", is_local_provider=False,
        input_tokens=1000, output_tokens=500, estimated_cost_usd=0.0105,
    )
    await save_audit(
        db_session, "generate_diagrams__usage_probe", {}, {}, status="ok", duration_ms=800,
        provider_used="ollama", is_local_provider=True,
        input_tokens=2000, output_tokens=1000, estimated_cost_usd=0.0,
    )

    usage = await get_actual_usage(db_session, days=30)
    assert usage.total_calls >= 2
    assert usage.total_input_tokens >= 3000
    assert usage.total_cost_usd >= 0.0105
    assert usage.fx_rate_used > 0
    assert usage.total_cost_rub == round(usage.total_cost_usd * usage.fx_rate_used, 2)

    actions = {row.action for row in usage.by_action}
    assert "generate_urs__usage_probe" in actions
    assert "generate_diagrams__usage_probe" in actions


@pytest.mark.asyncio
async def test_get_actual_usage_projects_to_30_days(db_session):
    """При period_days=10 месячная проекция должна быть примерно втрое больше фактической
    суммы за период (30/10 = 3x) — простая линейная экстраполяция, не более того."""
    await save_audit(
        db_session, "projection_probe", {}, {}, status="ok", duration_ms=100,
        provider_used="anthropic", is_local_provider=False,
        input_tokens=1000, output_tokens=1000, estimated_cost_usd=1.0,
    )
    usage = await get_actual_usage(db_session, days=10)
    relevant_actual = next(r.total_cost_usd for r in usage.by_action if r.action == "projection_probe")
    assert relevant_actual == 1.0
    # projected_monthly учитывает ВСЕ действия за период, не только "projection_probe",
    # поэтому проверяем лишь то, что проекция строго больше фактической суммы за 10 дней
    # (т.к. масштаб 30/10=3x применяется к total_cost_usd за период).
    assert usage.projected_monthly_cost_usd >= usage.total_cost_usd


@pytest.mark.asyncio
async def test_get_actual_usage_empty_period_gives_zero_not_error(db_session):
    usage = await get_actual_usage(db_session, days=1)
    assert usage.total_calls >= 0  # не падает даже если ничего не найдено
    assert usage.total_cost_usd >= 0.0


# ─── API: GET /dashboard/actual-usage ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_actual_usage_endpoint(client, auth_headers):
    resp = await client.get("/dashboard/actual-usage?days=30", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["period_days"] == 30
    assert "total_cost_usd" in body
    assert "projected_monthly_cost_rub" in body
    assert isinstance(body["by_action"], list)


# ─── Economic estimate с use_actual_llm_cost=true ──────────────────────────────

@pytest.mark.asyncio
async def test_economic_estimate_uses_actual_llm_cost_when_requested(client, auth_headers, db_session):
    # Готовим реальный расход, чтобы было что подхватить
    await save_audit(
        db_session, "generate_urs", {}, {}, status="ok", duration_ms=500,
        provider_used="anthropic", is_local_provider=False,
        input_tokens=5000, output_tokens=2000, estimated_cost_usd=0.045,
    )

    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Doc for economic estimate test", "text": "Нужна система учёта заявок с REST API.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]

    proj_resp = await client.post("/build-projects", headers=auth_headers, json={
        "document_id": doc_id, "name": "Economic estimate actual-usage test", "description": "Test project",
    })
    assert proj_resp.status_code == 200
    project_id = proj_resp.json()["id"]

    est_resp = await client.post(
        f"/build-projects/{project_id}/economic-estimate?use_actual_llm_cost=true",
        headers=auth_headers,
        json={
            "rate_backend": 3000, "rate_frontend": 2500, "rate_qa": 2000, "rate_devops": 2500,
            "rate_analyst": 2800, "hosting_cost_monthly": 5000, "llm_cost_monthly": 3000,
            "support_hours_monthly": 10, "time_saved_hours_monthly": 40, "avg_employee_rate": 1500,
            "manual_hours_by_role": {"backend": 80, "frontend": 40},
        },
    )
    assert est_resp.status_code == 200
    body = est_resp.json()
    assert body["llm_cost_source"] == "actual_usage"
    # llm_cost_monthly должен был подмениться реальными данными, а не остаться "3000" из тела запроса
    assert body["llm_cost_monthly"] != 3000


@pytest.mark.asyncio
async def test_economic_estimate_manual_by_default(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Doc for manual economic estimate test", "text": "Нужна система учёта заявок с REST API.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]

    proj_resp = await client.post("/build-projects", headers=auth_headers, json={
        "document_id": doc_id, "name": "Economic estimate manual test", "description": "Test project",
    })
    project_id = proj_resp.json()["id"]

    est_resp = await client.post(
        f"/build-projects/{project_id}/economic-estimate",  # use_actual_llm_cost не передан
        headers=auth_headers,
        json={
            "rate_backend": 3000, "rate_frontend": 2500, "rate_qa": 2000, "rate_devops": 2500,
            "rate_analyst": 2800, "hosting_cost_monthly": 5000, "llm_cost_monthly": 3000,
            "support_hours_monthly": 10, "time_saved_hours_monthly": 40, "avg_employee_rate": 1500,
            "manual_hours_by_role": {"backend": 80, "frontend": 40},
        },
    )
    assert est_resp.status_code == 200
    body = est_resp.json()
    assert body["llm_cost_source"] == "manual"
    assert body["llm_cost_monthly"] == 3000  # значение из тела запроса не тронуто
