"""
Тесты Фазы 2 — упрощённая матрица трассируемости (`GET /documents/{id}/coverage`).
Run: pytest tests/test_phase2_coverage.py -v
"""
import pytest


@pytest.mark.asyncio
async def test_coverage_empty_document_has_no_flags_set(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Coverage empty test",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]

    cov_resp = await client.get(f"/documents/{doc_id}/coverage", headers=auth_headers)
    assert cov_resp.status_code == 200
    body = cov_resp.json()
    assert body["document_id"] == doc_id
    assert body["has_requirements"] is False
    assert body["has_diagrams"] is False
    assert body["has_acceptance_criteria"] is False
    assert body["is_fully_covered"] is False
    assert body["requirements_source"] is None


@pytest.mark.asyncio
async def test_coverage_reflects_generated_diagrams(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Coverage diagrams test",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]

    await client.post(f"/documents/{doc_id}/generate-diagrams", headers=auth_headers)

    cov_resp = await client.get(f"/documents/{doc_id}/coverage", headers=auth_headers)
    body = cov_resp.json()
    assert body["has_diagrams"] is True
    assert body["diagrams_count"] > 0
    assert isinstance(body["diagrams_by_type"], list)
    assert len(body["diagrams_by_type"]) == body["diagrams_count"]


@pytest.mark.asyncio
async def test_coverage_prefers_urs_over_srs_when_both_exist(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Coverage URS/SRS priority test",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]

    await client.post(f"/documents/{doc_id}/generate-srs", headers=auth_headers)
    await client.post(f"/documents/{doc_id}/generate-urs", headers=auth_headers)

    cov_resp = await client.get(f"/documents/{doc_id}/coverage", headers=auth_headers)
    assert cov_resp.json()["requirements_source"] == "urs"


@pytest.mark.asyncio
async def test_coverage_falls_back_to_srs_when_no_urs(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Coverage SRS-only test",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]

    await client.post(f"/documents/{doc_id}/generate-srs", headers=auth_headers)

    cov_resp = await client.get(f"/documents/{doc_id}/coverage", headers=auth_headers)
    assert cov_resp.json()["requirements_source"] == "srs"


@pytest.mark.asyncio
async def test_coverage_reflects_review_acceptance_criteria_and_risks(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Coverage review test",
        "text": "Нужна система учёта заявок с REST API, базой данных PostgreSQL и JWT-аутентификацией.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]

    await client.post(f"/documents/{doc_id}/review", headers=auth_headers)

    cov_resp = await client.get(f"/documents/{doc_id}/coverage", headers=auth_headers)
    body = cov_resp.json()
    # На safe-fallback пути (нет LLM-ключа в тестовом окружении) acceptance_criteria может
    # быть пустым — проверяем структуру ответа, а не конкретное количество.
    assert isinstance(body["acceptance_criteria"], list)
    assert isinstance(body["risks_count"], int)
    assert isinstance(body["risks_high_count"], int)


@pytest.mark.asyncio
async def test_coverage_document_not_found_returns_404(client, auth_headers):
    resp = await client.get("/documents/does-not-exist/coverage", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_coverage_uses_document_default_standards(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Coverage standards test",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]
    await client.patch(f"/documents/{doc_id}/standards", headers=auth_headers, json={
        "default_requirements_standard": "GOST_34",
        "default_diagram_standard": "UML_ISO_19505",
    })

    cov_resp = await client.get(f"/documents/{doc_id}/coverage", headers=auth_headers)
    body = cov_resp.json()
    assert body["requirements_standard"] == "GOST_34"
    assert body["diagram_standard"] == "UML_ISO_19505"
