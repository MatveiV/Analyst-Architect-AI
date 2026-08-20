"""
Тесты Эпика B — справочник стандартов, генерация URS/SRS по стандарту, дефолты документа.
Run: pytest tests/test_epic_b_standards.py -v
"""
import json
import pytest

from app.services import doc_generator


# ─── B1: справочник стандартов ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_standards_returns_seeded_rows(client, auth_headers):
    resp = await client.get("/standards", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    ids = {row["id"] for row in data}
    # минимум ожидаемых из сида (0003 / standards_seed.py)
    assert {"C4_MODEL", "GOST_34", "ISO_IEC_IEEE_29148", "UML_ISO_19505"} <= ids
    for row in data:
        assert row["family"] in ("requirements", "diagram")


@pytest.mark.asyncio
async def test_list_standards_filters_by_family(client, auth_headers):
    resp = await client.get("/standards?family=requirements", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data, "должен быть хотя бы один requirements-стандарт"
    assert all(row["family"] == "requirements" for row in data)

    resp2 = await client.get("/standards?family=diagram", headers=auth_headers)
    data2 = resp2.json()
    assert all(row["family"] == "diagram" for row in data2)


# ─── B3: параметризация промптов URS/SRS по стандарту (unit-уровень) ─────────

class TestStandardSectionMap:
    def test_gost34_sections_are_russian_and_distinct_from_default(self):
        gost34 = doc_generator._sections_for("urs", "GOST_34")
        default = doc_generator._sections_for("urs", "ISO_IEC_IEEE_29148")
        assert gost34 != default
        assert any("Общие сведения" in s for s in gost34)

    def test_unknown_standard_falls_back_to_iso29148(self):
        sections = doc_generator._sections_for("urs", "NOT_A_REAL_STANDARD")
        assert sections == doc_generator._sections_for("urs", "ISO_IEC_IEEE_29148")

    def test_system_prompt_mentions_standard_id_and_sections(self):
        system = doc_generator._urs_system_for_standard("GOST_34")
        assert "GOST_34" in system
        assert "Общие сведения" in system


@pytest.mark.asyncio
async def test_generate_urs_fallback_preserves_standard_profile():
    """Нет LLM-ключа в тестовом окружении => детерминированный safe-fallback путь;
    даже на нём standard_profile должен сохраняться, иначе UI не сможет показать,
    какой стандарт запрашивался."""
    schema = await doc_generator.generate_urs("Нужна система учёта заявок.", title="T", standard="GOST_34")
    assert schema.standard_profile == "GOST_34"
    assert schema.needs_review is True
    assert schema.confidence == "low"


@pytest.mark.asyncio
async def test_generate_srs_fallback_preserves_standard_profile():
    schema = await doc_generator.generate_srs("Нужна система учёта заявок.", title="T", standard="IEEE_830")
    assert schema.standard_profile == "IEEE_830"
    assert schema.needs_review is True


# ─── B2/B5: персистентность URS/SRS + дефолтные стандарты документа ──────────

@pytest.mark.asyncio
async def test_document_standards_patch_roundtrip(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "TZ standards roundtrip",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]
    assert doc_resp.json()["default_requirements_standard"] is None

    patch_resp = await client.patch(f"/documents/{doc_id}/standards", headers=auth_headers, json={
        "default_requirements_standard": "GOST_34",
        "default_diagram_standard": "UML_ISO_19505",
    })
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["default_requirements_standard"] == "GOST_34"
    assert body["default_diagram_standard"] == "UML_ISO_19505"


@pytest.mark.asyncio
async def test_generate_urs_persists_requirements_document_and_uses_document_default(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "TZ URS persistence test",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]

    # Задаём дефолт документа — GOST_19 — и НЕ передаём ?standard= явно в generate-urs,
    # чтобы проверить, что дефолт документа реально применяется (Эпик B5).
    await client.patch(f"/documents/{doc_id}/standards", headers=auth_headers, json={
        "default_requirements_standard": "GOST_19",
    })

    gen_resp = await client.post(f"/documents/{doc_id}/generate-urs", headers=auth_headers)
    assert gen_resp.status_code == 200
    assert gen_resp.json()["standard_profile"] == "GOST_19"

    history_resp = await client.get(f"/documents/{doc_id}/requirements-documents", headers=auth_headers)
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 1
    assert history[0]["doc_kind"] == "urs"
    assert history[0]["standard_profile"] == "GOST_19"
    assert history[0]["needs_review"] is True  # безопасный fallback в тестовом окружении

    # Плоский эндпоинт получения одного requirements_document по id (Эпик B5)
    req_doc_id = history[0]["id"]
    single_resp = await client.get(f"/requirements-documents/{req_doc_id}", headers=auth_headers)
    assert single_resp.status_code == 200
    assert single_resp.json()["id"] == req_doc_id

    content = json.loads(single_resp.json()["content_json"])
    assert content["standard_profile"] == "GOST_19"


@pytest.mark.asyncio
async def test_generate_urs_explicit_standard_overrides_document_default(client, auth_headers):
    """Явный ?standard= в запросе должен иметь приоритет над дефолтом документа (Эпик B5)."""
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "TZ URS override test",
        "text": "Нужна система учёта заявок с REST API.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]
    await client.patch(f"/documents/{doc_id}/standards", headers=auth_headers, json={
        "default_requirements_standard": "GOST_19",
    })

    gen_resp = await client.post(
        f"/documents/{doc_id}/generate-urs?standard=IEEE_830", headers=auth_headers,
    )
    assert gen_resp.json()["standard_profile"] == "IEEE_830"


@pytest.mark.asyncio
async def test_requirements_document_not_found_returns_404(client, auth_headers):
    resp = await client.get("/requirements-documents/does-not-exist", headers=auth_headers)
    assert resp.status_code == 404
