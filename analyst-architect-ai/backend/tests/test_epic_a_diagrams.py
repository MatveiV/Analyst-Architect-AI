"""
Тесты Эпика A — локальный рендер диаграмм, версии/rollback, встраивание в DOCX.
Run: pytest tests/test_epic_a_diagrams.py -v
"""
import io
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from app.services import diagram_engine
from app.services.export_service import export_document_docx


# ─── A1/A2: render_diagram() — локальный рендер + честный fallback/blocked ───

class TestRenderDiagram:
    @pytest.mark.asyncio
    async def test_unknown_notation_fails_fast(self):
        result = await diagram_engine.render_diagram("code", "unknown_notation")
        assert result["render_status"] == "failed"
        assert result["render_svg"] is None
        assert result["render_png"] is None

    @pytest.mark.asyncio
    async def test_kroki_success_returns_ok(self):
        """Успешный ответ Kroki (200/200) должен дать render_status='ok' с байтами svg/png."""
        class _Resp:
            def __init__(self, status_code, text="<svg/>", content=b"\x89PNG"):
                self.status_code = status_code
                self.text = text
                self.content = content

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.side_effect = [_Resp(200), _Resp(200)]

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await diagram_engine.render_diagram("@startuml\n@enduml", "plantuml")

        assert result["render_status"] == "ok"
        assert result["render_svg"] == "<svg/>"
        assert result["render_png"] == b"\x89PNG"
        assert result["render_error"] is None

    @pytest.mark.asyncio
    async def test_kroki_unreachable_falls_back_external_by_default(self):
        """Эпик A1: при недоступном Kroki и ENFORCE_LOCAL_ONLY=false — external_fallback, не падаем."""
        with patch("httpx.AsyncClient", side_effect=ConnectionError("no route")), \
             patch("app.services.diagram_engine.settings") as mock_settings:
            mock_settings.DIAGRAM_RENDERER_URL = "http://kroki:8000"
            mock_settings.DIAGRAM_RENDERER_TIMEOUT = 1
            mock_settings.ENFORCE_LOCAL_ONLY = False
            result = await diagram_engine.render_diagram("@startuml\n@enduml", "plantuml")

        assert result["render_status"] == "external_fallback"
        assert result["render_svg"] is None

    @pytest.mark.asyncio
    async def test_enforce_local_only_blocks_external_fallback(self):
        """
        Эпик C5 (проверяется здесь, т.к. это поведение самого render_diagram):
        при ENFORCE_LOCAL_ONLY=true недоступность Kroki должна давать blocked_external,
        а НЕ external_fallback — система не должна тихо предполагать уход во внешний сервис.
        """
        with patch("httpx.AsyncClient", side_effect=ConnectionError("no route")), \
             patch("app.services.diagram_engine.settings") as mock_settings:
            mock_settings.DIAGRAM_RENDERER_URL = "http://kroki:8000"
            mock_settings.DIAGRAM_RENDERER_TIMEOUT = 1
            mock_settings.ENFORCE_LOCAL_ONLY = True
            result = await diagram_engine.render_diagram("@startuml\n@enduml", "plantuml")

        assert result["render_status"] == "blocked_external"
        assert "ENFORCE_LOCAL_ONLY" in result["render_error"] or "запрещает" in result["render_error"]


# ─── A2/B4: generate_all_diagrams — приближённые стандарты форсируют needs_review ──

class TestGenerateAllDiagramsStandards:
    @pytest.mark.asyncio
    async def test_fallback_carries_standard_profile(self):
        """Даже на safe-fallback пути (нет LLM-ключа в тестовом окружении) standard_profile
        должен сохраняться в результате — иначе UI не сможет показать, какой стандарт применён."""
        schema = await diagram_engine.generate_all_diagrams(
            "Система для учёта заявок", title="Test", standard="UML_ISO_19505",
        )
        assert schema.standard_profile == "UML_ISO_19505"
        assert schema.needs_review is True  # нет LLM-ключа в тестовом окружении => fallback

    @pytest.mark.asyncio
    async def test_approximate_standard_forces_low_confidence(self):
        """Эпик B4: ГОСТ 19.701 — приближённая генерация, needs_review должен быть True
        даже если бы LLM вернул валидный ответ (проверяем на уровне безопасного fallback,
        т.к. реального LLM-провайдера в тестовом окружении нет)."""
        schema = await diagram_engine.generate_all_diagrams(
            "Система для учёта заявок", title="Test", standard="GOST_19_701",
        )
        assert schema.needs_review is True
        assert schema.standard_profile == "GOST_19_701"

    def test_approximate_standards_set_contains_expected(self):
        assert "GOST_19_701" in diagram_engine.APPROXIMATE_DIAGRAM_STANDARDS
        assert "IEC_61082" in diagram_engine.APPROXIMATE_DIAGRAM_STANDARDS
        assert "C4_MODEL" not in diagram_engine.APPROXIMATE_DIAGRAM_STANDARDS

    def test_standard_instruction_map_covers_all_seeded_diagram_standards(self):
        """Каждый diagram-стандарт из сида (B1) должен иметь инструкцию, иначе он молча
        свалится на C4 в рантайме без явного предупреждения разработчику."""
        seeded_diagram_ids = {
            row["id"] for row in __import__(
                "app.services.standards_seed", fromlist=["SEED_STANDARDS"]
            ).SEED_STANDARDS if row["family"] == "diagram"
        }
        assert seeded_diagram_ids <= set(diagram_engine.STANDARD_DIAGRAM_INSTRUCTIONS.keys())


# ─── Integration: /documents/{id}/generate-diagrams + versioning endpoints ────

@pytest.mark.asyncio
async def test_generate_diagrams_creates_artifacts_with_render_status(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "TZ for diagram test",
        "text": "Нужна система для учёта заявок с REST API и базой данных.",
        "doc_type": "tz",
    })
    assert doc_resp.status_code == 200
    doc_id = doc_resp.json()["id"]

    gen_resp = await client.post(f"/documents/{doc_id}/generate-diagrams", headers=auth_headers)
    assert gen_resp.status_code == 200
    body = gen_resp.json()
    assert body["created"], "должна быть создана хотя бы одна диаграмма"
    for item in body["created"]:
        assert item["render_status"] in ("ok", "failed", "external_fallback", "blocked_external")
    assert body["standard_profile"] == "C4_MODEL"  # дефолт, явный standard не передавали

    diagrams_resp = await client.get(f"/diagrams/document/{doc_id}", headers=auth_headers)
    assert diagrams_resp.status_code == 200
    diagrams = diagrams_resp.json()
    assert len(diagrams) == len(body["created"])
    return diagrams  # используется следующим тестом через явный вызов ниже


@pytest.mark.asyncio
async def test_diagram_update_creates_version_and_allows_rollback(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "TZ for versioning test",
        "text": "Нужна система для учёта заявок с REST API.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]
    gen_resp = await client.post(f"/documents/{doc_id}/generate-diagrams", headers=auth_headers)
    diagram_id = gen_resp.json()["created"][0]["type"]  # placeholder; fetch real id below

    diagrams = (await client.get(f"/diagrams/document/{doc_id}", headers=auth_headers)).json()
    diagram_id = diagrams[0]["id"]
    original_code = diagrams[0]["source_code"]

    # Правка (Эпик A3)
    put_resp = await client.put(f"/diagrams/{diagram_id}", headers=auth_headers, json={
        "source_code": "@startuml\ntitle Edited by test\n@enduml",
        "change_note": "test edit",
    })
    assert put_resp.status_code == 200
    assert put_resp.json()["source_code"] == "@startuml\ntitle Edited by test\n@enduml"

    # История версий должна содержать оригинал под версией 1
    versions_resp = await client.get(f"/diagrams/{diagram_id}/versions", headers=auth_headers)
    assert versions_resp.status_code == 200
    versions = versions_resp.json()
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["source_code"] == original_code
    assert versions[0]["change_note"] == "test edit"

    # Rollback к версии 1 должен вернуть оригинальный код и создать версию 2 (не терять историю)
    rollback_resp = await client.post(f"/diagrams/{diagram_id}/rollback/1", headers=auth_headers)
    assert rollback_resp.status_code == 200
    assert rollback_resp.json()["source_code"] == original_code

    versions_after = (await client.get(f"/diagrams/{diagram_id}/versions", headers=auth_headers)).json()
    assert len(versions_after) == 2  # rollback не удаляет историю, а добавляет запись

    # Rollback к несуществующей версии — 404, не 500
    bad_rollback = await client.post(f"/diagrams/{diagram_id}/rollback/999", headers=auth_headers)
    assert bad_rollback.status_code == 404


# ─── A4: встраивание диаграмм в DOCX ──────────────────────────────────────────

class TestExportWithDiagrams:
    def test_export_without_diagrams_still_works(self):
        docx_bytes = export_document_docx("Test Doc", {"summary": "Резюме", "confidence": "high", "needs_review": False})
        assert docx_bytes[:2] == b"PK"  # docx — это zip-контейнер

    def test_export_embeds_diagram_image_when_rendered(self):
        # Минимальный валидный 1x1 прозрачный PNG (реальные байты, а не заглушка) —
        # python-docx парсит PNG-заголовок, поэтому фейковых байтов недостаточно.
        import base64
        tiny_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )

        class _FakeDiagram:
            diagram_type = "c4_context"
            notation = "plantuml"
            source_code = "@startuml\n@enduml"
            render_png = tiny_png
            render_status = "ok"
            standard_profile = "C4_MODEL"

        docx_bytes = export_document_docx(
            "Test Doc",
            {"summary": "Резюме", "confidence": "high", "needs_review": False, "standard_profile": "C4_MODEL"},
            diagrams=[_FakeDiagram()],
        )
        assert docx_bytes[:2] == b"PK"

    def test_export_shows_reason_when_render_missing(self):
        """Если render_png нет — в документ должен попасть код диаграммы и явная причина,
        а не пустая секция или падение экспорта."""
        class _FakeDiagram:
            diagram_type = "erd"
            notation = "plantuml"
            source_code = "@startuml\nentity Foo {}\n@enduml"
            render_png = None
            render_status = "blocked_external"
            standard_profile = None

        docx_bytes = export_document_docx(
            "Test Doc",
            {"confidence": "low", "needs_review": True},
            diagrams=[_FakeDiagram()],
        )
        assert docx_bytes[:2] == b"PK"
        from docx import Document
        doc = Document(io.BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "заблокирован" in full_text or "ENFORCE_LOCAL_ONLY" in full_text
        assert "entity Foo" in full_text
