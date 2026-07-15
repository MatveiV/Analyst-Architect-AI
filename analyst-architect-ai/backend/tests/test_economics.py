"""
Tests for the economic module: build projects, task estimation, ROI/payback formulas.
"""
import pytest
from app.services.economics_service import (
    compute_capex, compute_opex_monthly, compute_benefit_monthly,
    compute_payback_months, compute_roi_12m_pct, full_economic_calculation,
    compute_variance,
)
from app.schemas import EconomicEstimateIn


# ─── Unit tests: pure formulas ───────────────────────────────────────────────

class TestEconomicsFormulas:
    def _rates(self, **overrides):
        defaults = dict(
            rate_backend=2500, rate_frontend=2200, rate_qa=1800, rate_devops=2800,
            rate_analyst=2500, hosting_cost_monthly=5000, llm_cost_monthly=3000,
            support_hours_monthly=8, time_saved_hours_monthly=100, avg_employee_rate=2500,
        )
        defaults.update(overrides)
        return EconomicEstimateIn(**defaults)

    def test_capex_matches_manual_sum(self):
        rates = self._rates()
        hours = {"backend": 100, "frontend": 50}
        capex = compute_capex(hours, rates)
        assert capex == 100 * 2500 + 50 * 2200

    def test_capex_unknown_role_falls_back_to_analyst_rate(self):
        rates = self._rates()
        hours = {"unknown_role": 10}
        capex = compute_capex(hours, rates)
        assert capex == 10 * rates.rate_analyst

    def test_opex_includes_hosting_llm_and_support(self):
        rates = self._rates(hosting_cost_monthly=1000, llm_cost_monthly=500, support_hours_monthly=2, rate_backend=1000)
        opex = compute_opex_monthly(rates)
        assert opex == 1000 + 500 + 2 * 1000

    def test_benefit_is_time_saved_times_rate(self):
        rates = self._rates(time_saved_hours_monthly=50, avg_employee_rate=2000)
        benefit = compute_benefit_monthly(rates)
        assert benefit == 50 * 2000

    def test_payback_positive_case(self):
        payback = compute_payback_months(capex=100_000, benefit_monthly=20_000, opex_monthly=5_000)
        assert payback == round(100_000 / 15_000, 1)

    def test_payback_never_pays_back_returns_negative_one(self):
        payback = compute_payback_months(capex=100_000, benefit_monthly=1_000, opex_monthly=5_000)
        assert payback == -1.0

    def test_roi_zero_capex_returns_zero(self):
        roi = compute_roi_12m_pct(capex=0, benefit_monthly=1000, opex_monthly=100)
        assert roi == 0.0

    def test_roi_positive_case(self):
        roi = compute_roi_12m_pct(capex=100_000, benefit_monthly=20_000, opex_monthly=5_000)
        expected = ((15_000 * 12) - 100_000) / 100_000 * 100
        assert roi == round(expected, 1)

    def test_full_calculation_pipeline(self):
        rates = self._rates()
        hours = {"backend": 120, "frontend": 80, "qa": 40, "devops": 16}
        result = full_economic_calculation(hours, rates)
        assert set(result.keys()) == {"capex", "opex_monthly", "benefit_monthly", "payback_months", "roi_12m_pct"}
        assert result["capex"] > 0
        assert result["payback_months"] > 0  # benefit (250,000) > opex in this scenario

    def test_variance_computation(self):
        estimate = {"capex": 100_000, "opex_monthly": 5_000, "benefit_monthly": 20_000}
        actual = {"actual_capex": 110_000, "actual_opex_monthly": 5_000, "actual_benefit_monthly": 18_000}
        variance = compute_variance(estimate, actual)
        assert variance["capex"]["delta"] == 10_000
        assert variance["capex"]["delta_pct"] == 10.0
        assert variance["benefit_monthly"]["delta"] == -2_000


# ─── Integration tests: build-projects API ──────────────────────────────────

@pytest.mark.asyncio
async def test_create_build_project_requires_valid_document(client, auth_headers):
    resp = await client.post("/build-projects", headers=auth_headers, json={
        "document_id": "nonexistent-id",
        "name": "Test Project",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_full_build_project_lifecycle(client, auth_headers):
    # Create source document
    doc = await client.post("/documents", headers=auth_headers, json={
        "title": "Внутренний портал документов",
        "text": "Нужен портал для хранения и поиска внутренних документов компании с версионированием и правами доступа.",
        "doc_type": "tz",
    })
    assert doc.status_code == 200
    doc_id = doc.json()["id"]

    # Create build project
    proj = await client.post("/build-projects", headers=auth_headers, json={
        "document_id": doc_id,
        "name": "Document Portal",
        "description": "Внутренний портал",
    })
    assert proj.status_code == 200
    project_id = proj.json()["id"]
    assert proj.json()["status"] == "draft"

    # List includes the new project
    listing = await client.get("/build-projects", headers=auth_headers)
    assert listing.status_code == 200
    assert any(p["id"] == project_id for p in listing.json())

    # Get by id
    got = await client.get(f"/build-projects/{project_id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["name"] == "Document Portal"

    # Economic estimate without any task estimate and without manual hours -> 400
    no_hours = await client.post(f"/build-projects/{project_id}/economic-estimate", headers=auth_headers, json={})
    assert no_hours.status_code == 400

    # Economic estimate with manual hours -> 200, numbers computed
    estimate = await client.post(
        f"/build-projects/{project_id}/economic-estimate",
        headers=auth_headers,
        json={"manual_hours_by_role": {"backend": 40, "frontend": 20}, "time_saved_hours_monthly": 30},
    )
    assert estimate.status_code == 200
    body = estimate.json()
    assert body["capex"] == 40 * 2500 + 20 * 2200  # default rates
    assert "roi_12m_pct" in body
    assert "payback_months" in body

    # Project status advances after estimate
    got2 = await client.get(f"/build-projects/{project_id}", headers=auth_headers)
    assert got2.json()["status"] == "approved"

    # Add actuals
    actual = await client.post(f"/build-projects/{project_id}/actuals", headers=auth_headers, json={
        "actual_capex": body["capex"],
        "actual_opex_monthly": body["opex_monthly"],
        "actual_benefit_monthly": body["benefit_monthly"],
        "notes": "Совпало с планом",
    })
    assert actual.status_code == 200

    # Status -> delivered
    got3 = await client.get(f"/build-projects/{project_id}", headers=auth_headers)
    assert got3.json()["status"] == "delivered"

    # Report includes variance (zero delta since actual == estimate)
    report = await client.get(f"/build-projects/{project_id}/report", headers=auth_headers)
    assert report.status_code == 200
    report_data = report.json()
    assert report_data["variance"]["capex"]["delta"] == 0

    # DOCX export works
    docx = await client.get(f"/build-projects/{project_id}/export/docx", headers=auth_headers)
    assert docx.status_code == 200
    assert docx.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@pytest.mark.asyncio
async def test_build_projects_require_auth(client):
    resp = await client.get("/build-projects")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_stats_shape(client, auth_headers):
    resp = await client.get("/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "documents" in data
    assert "reviews" in data
    assert "audit" in data
    assert "economics" in data
    assert "avg_roi_12m_pct" in data["economics"]


@pytest.mark.asyncio
async def test_seed_endpoints_require_admin(client, auth_headers):
    """auth_headers logs in as `analyst`; seed is admin-only."""
    resp = await client.post("/seed/documents", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_seed_endpoints_work_for_admin(client):
    login = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/seed/documents", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["loaded"] >= 1
