"""
Тесты Фазы 3 — авто-индексация артефактов в KB (URS/SRS/ADR/диаграммы/уроки).
Run: pytest tests/test_phase3_kb_autoindex.py -v
"""
import pytest
from app.services import kb_autoindex


# ─── Текстовые сборщики (unit) ────────────────────────────────────────────────

class TestTextBuilders:
    def test_urs_to_text_includes_requirements_and_stakeholders(self):
        text = kb_autoindex.urs_to_text({
            "title": "URS X",
            "objective": "Автоматизировать учёт заявок",
            "stakeholders": ["Клиент", "Оператор поддержки"],
            "user_requirements": [{"id": "UR-001", "description": "Форма заявки", "priority": "high"}],
            "constraints": ["Только веб-интерфейс"],
        }, title="fallback title")
        assert "URS X" in text
        assert "Клиент" in text
        assert "UR-001" in text
        assert "Форма заявки" in text
        assert "Только веб-интерфейс" in text

    def test_urs_to_text_falls_back_to_passed_title_when_missing(self):
        text = kb_autoindex.urs_to_text({}, title="Fallback Title")
        assert "Fallback Title" in text

    def test_adr_to_text_includes_alternatives_and_consequences(self):
        text = kb_autoindex.adr_to_text({
            "title": "ADR: выбор БД",
            "status": "accepted",
            "context": "Нужна БД для очередей",
            "problem": "SQLite не тянет параллелизм",
            "decision": "Использовать PostgreSQL",
            "alternatives": [{"option": "MongoDB", "reason_rejected": "нет транзакций"}],
            "consequences": {"positive": ["Надёжность"], "negative": ["Доп. инфраструктура"]},
        }, title="fallback")
        assert "PostgreSQL" in text
        assert "MongoDB" in text
        assert "нет транзакций" in text
        assert "Надёжность" in text
        assert "Доп. инфраструктура" in text

    def test_diagrams_to_text_includes_type_and_code_excerpt(self):
        diagram_map = {"c4_context": ("plantuml", "@startuml\ntitle Context\nPerson(user, \"User\")\n@enduml")}
        text = kb_autoindex.diagrams_to_text(diagram_map, "MySystem", "C4_MODEL")
        assert "MySystem" in text
        assert "C4_MODEL" in text
        assert "c4_context" in text
        assert "Person(user" in text

    def test_diagrams_to_text_skips_empty_code(self):
        diagram_map = {"erd": ("plantuml", "")}
        text = kb_autoindex.diagrams_to_text(diagram_map, "Sys", "C4_MODEL")
        assert "erd" not in text  # пустой код диаграммы не должен попадать в текст

    def test_lesson_to_text_includes_recommendation(self):
        text = kb_autoindex.lesson_to_text(
            "Недооценили интеграцию", "Оценка интеграции с 1С заняла в 3 раза больше времени",
            "estimation", "negative", "Не учли легаси-формат обмена",
            "В следующий раз закладывать 3x на интеграции с 1С",
        )
        assert "Недооценили интеграцию" in text
        assert "легаси-формат" in text
        assert "3x на интеграции" in text


# ─── autoindex_artifact() — интеграция с БД и RAG ─────────────────────────────

@pytest.mark.asyncio
async def test_autoindex_artifact_creates_kb_article_document(db_session):
    doc = await kb_autoindex.autoindex_artifact(
        db_session, title="Test artifact", text="Осмысленный текст для поиска про заявки и REST API.",
        source_type="urs", source_id="req-123", project_name="Project X",
    )
    assert doc is not None
    assert doc.doc_type == "kb_article"
    assert doc.source_type == "urs"
    assert doc.source_id == "req-123"
    assert doc.title.startswith("[Авто]")


@pytest.mark.asyncio
async def test_autoindex_artifact_returns_none_for_empty_text(db_session):
    doc = await kb_autoindex.autoindex_artifact(
        db_session, title="Empty", text="   ", source_type="urs", source_id="req-1",
    )
    assert doc is None


@pytest.mark.asyncio
async def test_autoindexed_document_appears_in_kb_documents_list(client, auth_headers):
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "KB autoindex integration test",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]

    # generate-urs на safe-fallback пути (нет LLM-ключа) даёт needs_review=True -> НЕ индексируется
    # (осознанное решение: не засорять KB неуверенными заглушками). Поэтому здесь проверяем
    # именно то, что "уверенный" путь ИМЕЛ БЫ эффект — через прямой вызов autoindex_artifact,
    # т.к. воспроизвести "уверенный" LLM-ответ без реального провайдера в тестах нельзя.
    from app.services import kb_autoindex as kb
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await kb.autoindex_artifact(
            db, title=f"URS: KB autoindex integration test",
            text="URS: система учёта заявок с REST API",
            source_type="urs", source_id="req-test-1",
        )

    kb_docs = await client.get("/kb/documents", headers=auth_headers)
    assert kb_docs.status_code == 200
    titles = [d["title"] for d in kb_docs.json()]
    assert any("URS: KB autoindex integration test" in t for t in titles)


@pytest.mark.asyncio
async def test_needs_review_urs_is_not_autoindexed(client, auth_headers):
    """Safe-fallback (needs_review=True, "требует ручного заполнения") НЕ должен попадать
    в KB — иначе следующая генерация будет опираться на пустышку, выданную за прошлый опыт."""
    doc_resp = await client.post("/documents", headers=auth_headers, json={
        "title": "No-autoindex-on-fallback test",
        "text": "Нужна система учёта заявок с REST API и базой данных PostgreSQL.",
        "doc_type": "tz",
    })
    doc_id = doc_resp.json()["id"]

    urs_resp = await client.post(f"/documents/{doc_id}/generate-urs", headers=auth_headers)
    assert urs_resp.json()["needs_review"] is True  # тестовое окружение без LLM-ключа

    kb_docs = await client.get("/kb/documents", headers=auth_headers)
    titles = [d["title"] for d in kb_docs.json()]
    assert not any("No-autoindex-on-fallback test" in t for t in titles)


@pytest.mark.asyncio
async def test_manual_lesson_creation_is_autoindexed(client, auth_headers):
    resp = await client.post("/lessons", headers=auth_headers, json={
        "title": "Ручной урок для теста автоиндексации",
        "description": "Заказчик поменял требования на середине спринта",
        "category": "process",
        "impact_type": "negative",
        "recommendation": "Фиксировать скоуп спринта письменно перед стартом",
    })
    assert resp.status_code == 200

    kb_docs = await client.get("/kb/documents", headers=auth_headers)
    titles = [d["title"] for d in kb_docs.json()]
    assert any("Ручной урок для теста автоиндексации" in t for t in titles)


@pytest.mark.asyncio
async def test_kb_snippets_retrieve_autoindexed_lesson(client, auth_headers, db_session):
    """Сквозная проверка: урок, добавленный через /lessons, реально находится через
    гибридный поиск RAG (retrieve_snippets) — именно это и было целью автоиндексации.
    /kb/ask целиком не тестируем здесь: он ещё и синтезирует ответ через LLM, чего в
    тестовом окружении без ключа нет — это уже поведение самого /kb/ask, не автоиндексации."""
    unique_marker = "УникальнаяФразаДляПоискаУрокаXYZ123"
    resp = await client.post("/lessons", headers=auth_headers, json={
        "title": f"Урок про {unique_marker}",
        "description": f"Мы столкнулись с проблемой {unique_marker} при интеграции с банком.",
        "category": "technology",
        "impact_type": "negative",
        "recommendation": f"В следующий раз проверять {unique_marker} заранее.",
    })
    assert resp.status_code == 200

    from app.services import rag_engine
    results = await rag_engine.retrieve_snippets(db_session, unique_marker, top_k=5)
    assert len(results) > 0
    assert any(unique_marker in snippet.snippet_text for snippet, score in results)
