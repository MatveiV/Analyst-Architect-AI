"""
Тесты Фазы 2 — сравнение двух рецензий одного документа (`GET /reviews/diff`).
Run: pytest tests/test_phase2_review_diff.py -v
"""
import pytest


@pytest.mark.asyncio
async def test_diff_two_reviews_of_same_document(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Diff test doc",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]

    rev1 = await client.post(f"/documents/{doc_id}/review", headers=auth_headers)
    rev2 = await client.post(f"/documents/{doc_id}/review", headers=auth_headers)
    rev1_id = rev1.json()["id"]
    rev2_id = rev2.json()["id"]

    diff_resp = await client.get(f"/reviews/diff?from_id={rev1_id}&to_id={rev2_id}", headers=auth_headers)
    assert diff_resp.status_code == 200
    body = diff_resp.json()
    assert body["from_review_id"] == rev1_id
    assert body["to_review_id"] == rev2_id
    assert isinstance(body["risks_added"], list)
    assert isinstance(body["risks_removed"], list)
    assert isinstance(body["summary_diff_lines"], list)


@pytest.mark.asyncio
async def test_diff_detects_needs_review_and_confidence_change():
    """Unit-уровень: compute_review_diff() должен честно отмечать смену confidence/needs_review,
    а также added/removed элементы списков — без похода в БД."""
    from app.services.diff_service import compute_review_diff
    from app.models.review import Review
    from datetime import datetime
    import json

    from_review = Review(
        id="r1", document_id="d1", created_at=datetime(2026, 1, 1),
        review_json=json.dumps({
            "summary": "Старое резюме.",
            "risks": [{"severity": "low", "description": "Риск A"}],
            "acceptance_criteria": ["Критерий 1"],
            "missing_requirements": ["Нет данных о нагрузке"],
        }),
        needs_review=True, confidence="low",
    )
    to_review = Review(
        id="r2", document_id="d1", created_at=datetime(2026, 1, 2),
        review_json=json.dumps({
            "summary": "Новое резюме.",
            "risks": [{"severity": "low", "description": "Риск A"}, {"severity": "high", "description": "Риск B"}],
            "acceptance_criteria": ["Критерий 1", "Критерий 2"],
            "missing_requirements": [],
        }),
        needs_review=False, confidence="high",
    )

    diff = compute_review_diff(from_review, to_review)
    assert diff.confidence_changed is True
    assert diff.confidence_from == "low"
    assert diff.confidence_to == "high"
    assert diff.needs_review_changed is True
    assert diff.needs_review_from is True
    assert diff.needs_review_to is False
    assert diff.risks_added == ["Риск B"]
    assert diff.risks_removed == []
    assert diff.acceptance_criteria_added == ["Критерий 2"]
    assert diff.missing_requirements_removed == ["Нет данных о нагрузке"]
    assert len(diff.summary_diff_lines) > 0


@pytest.mark.asyncio
async def test_diff_no_change_gives_empty_added_removed():
    from app.services.diff_service import compute_review_diff
    from app.models.review import Review
    from datetime import datetime
    import json

    identical_json = json.dumps({
        "summary": "Одно и то же резюме.",
        "risks": [{"severity": "medium", "description": "Риск X"}],
        "acceptance_criteria": ["Критерий 1"],
        "missing_requirements": [],
    })
    r1 = Review(id="r1", document_id="d1", created_at=datetime(2026, 1, 1),
                review_json=identical_json, needs_review=False, confidence="high")
    r2 = Review(id="r2", document_id="d1", created_at=datetime(2026, 1, 2),
                review_json=identical_json, needs_review=False, confidence="high")

    diff = compute_review_diff(r1, r2)
    assert diff.confidence_changed is False
    assert diff.needs_review_changed is False
    assert diff.risks_added == []
    assert diff.risks_removed == []
    assert diff.summary_diff_lines == []


@pytest.mark.asyncio
async def test_diff_missing_review_returns_404(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Diff 404 test",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]
    rev = await client.post(f"/documents/{doc_id}/review", headers=auth_headers)
    rev_id = rev.json()["id"]

    resp = await client.get(f"/reviews/diff?from_id={rev_id}&to_id=does-not-exist", headers=auth_headers)
    assert resp.status_code == 404

    resp2 = await client.get(f"/reviews/diff?from_id=does-not-exist&to_id={rev_id}", headers=auth_headers)
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_list_reviews_filters_by_document_id(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "Filter by doc test",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]
    await client.post(f"/documents/{doc_id}/review", headers=auth_headers)

    resp = await client.get(f"/reviews?document_id={doc_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert all(r["document_id"] == doc_id for r in resp.json())
    assert len(resp.json()) >= 1
