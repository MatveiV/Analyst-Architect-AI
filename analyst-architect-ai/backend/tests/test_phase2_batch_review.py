"""
Тесты Фазы 2 — «Пакетная рецензия» (batch review).
Run: pytest tests/test_phase2_batch_review.py -v
"""
import pytest


@pytest.mark.asyncio
async def test_create_batch_review_processes_all_items(client, auth_headers):
    resp = await client.post("/batch-reviews", headers=auth_headers, json={
        "title": "Batch test run",
        "items": [
            {"title": "TZ 1", "text": "Нужна система учёта заявок с REST API и базой данных."},
            {"title": "TZ 2", "text": "Сделать сайт."},  # заведомо "сырое" -> needs_review
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 2
    assert body["completed_count"] == 2
    assert body["status"] in ("completed", "completed_with_errors")
    assert len(body["items"]) == 2
    for item in body["items"]:
        assert item["status"] in ("ok", "error")
        assert item["document_id"] is not None


@pytest.mark.asyncio
async def test_batch_review_vague_item_flags_needs_review(client, auth_headers):
    resp = await client.post("/batch-reviews", headers=auth_headers, json={
        "items": [{"title": "Слишком короткое ТЗ", "text": "Сделать сайт."}],
    })
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["needs_review"] is True
    assert resp.json()["needs_review_count"] == 1


@pytest.mark.asyncio
async def test_list_and_get_batch_review(client, auth_headers):
    create_resp = await client.post("/batch-reviews", headers=auth_headers, json={
        "title": "List/detail test",
        "items": [{"title": "TZ A", "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL."}],
    })
    batch_id = create_resp.json()["id"]

    list_resp = await client.get("/batch-reviews", headers=auth_headers)
    assert list_resp.status_code == 200
    assert any(b["id"] == batch_id for b in list_resp.json())

    detail_resp = await client.get(f"/batch-reviews/{batch_id}", headers=auth_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == batch_id
    assert len(detail_resp.json()["items"]) == 1


@pytest.mark.asyncio
async def test_batch_review_detail_filters_by_needs_review(client, auth_headers):
    create_resp = await client.post("/batch-reviews", headers=auth_headers, json={
        "items": [
            {"title": "Нормальное ТЗ", "text": "Нужна система учёта заявок с REST API, базой данных PostgreSQL и JWT-аутентификацией пользователей через личный кабинет."},
            {"title": "Сырое ТЗ", "text": "Сделать сайт."},
        ],
    })
    batch_id = create_resp.json()["id"]

    filtered = await client.get(f"/batch-reviews/{batch_id}?needs_review=true", headers=auth_headers)
    assert filtered.status_code == 200
    assert all(item["needs_review"] is True for item in filtered.json()["items"])
    assert len(filtered.json()["items"]) >= 1  # хотя бы "Сырое ТЗ" точно даст needs_review=true


@pytest.mark.asyncio
async def test_batch_review_not_found_returns_404(client, auth_headers):
    resp = await client.get("/batch-reviews/does-not-exist", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_batch_review_export_csv(client, auth_headers):
    create_resp = await client.post("/batch-reviews", headers=auth_headers, json={
        "items": [{"title": "CSV export test", "text": "Нужна система учёта заявок с REST API и базой данных."}],
    })
    batch_id = create_resp.json()["id"]

    csv_resp = await client.get(f"/batch-reviews/{batch_id}/export/csv", headers=auth_headers)
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    text = csv_resp.content.decode("utf-8-sig")
    assert "CSV export test" in text
    assert "needs_review" in text  # заголовок колонки


@pytest.mark.asyncio
async def test_batch_review_rejects_empty_items_list(client, auth_headers):
    resp = await client.post("/batch-reviews", headers=auth_headers, json={"items": []})
    assert resp.status_code == 422  # min_length=1 на items


@pytest.mark.asyncio
async def test_batch_review_creates_underlying_documents_and_reviews(client, auth_headers):
    """Каждый элемент батча должен создать полноценный Document + Review, доступные
    через обычные /documents и /reviews эндпоинты — батч не создаёт параллельную
    систему хранения, а переиспользует существующую."""
    create_resp = await client.post("/batch-reviews", headers=auth_headers, json={
        "items": [{"title": "Reuse check", "text": "Нужна система учёта заявок с REST API и базой данных."}],
    })
    item = create_resp.json()["items"][0]

    doc_resp = await client.get(f"/documents/{item['document_id']}", headers=auth_headers)
    assert doc_resp.status_code == 200
    assert doc_resp.json()["title"] == "Reuse check"

    if item["review_id"]:
        review_resp = await client.get(f"/reviews/{item['review_id']}", headers=auth_headers)
        assert review_resp.status_code == 200
