"""
Градуационные контрольные тесты: сверка с требованиями fix-prompt-analyst-architect-ai.md
(Шаг 10.7). Проверяют НАЛИЧИЕ обязательных эндпоинтов обеих групп (без вызова LLM)
и СТРУКТУРУ тестовых данных. Не зависят от внешних провайдеров.
"""
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DATA = REPO_ROOT / "tests_data"


# ─── Обязательные точки доступа (Option2 §2 / Option5 §2 / fix-prompt §3) ─────
REQUIRED_ENDPOINTS = [
    # Группа A — ИИ-рецензент (Вариант 2)
    "POST /documents",
    "POST /documents/{doc_id}/review",
    "GET /reviews/{review_id}",
    "POST /ai/review",
    # Группа B — Система знаний (Вариант 5)
    "POST /kb/documents",
    "GET /kb/documents",
    "POST /kb/ask",
    "POST /ai/answer_with_sources",
]


def _route_set():
    routes = {}
    for r in app.routes:
        for method in getattr(r, "methods", []) or []:
            routes[f"{method} {r.path}"] = True
    return routes


def _path_variants_match(routes, method, path):
    for rp in routes:
        if not rp.startswith(method):
            continue
        a_seg = [s for s in rp.split("/") if not s.startswith("{")]
        b_seg = [s for s in path.split("/") if not s.startswith("{")]
        if a_seg == b_seg:
            return True
    return False


def test_required_endpoints_registered():
    routes = _route_set()
    missing = []
    for ep in REQUIRED_ENDPOINTS:
        method, path = ep.split(" ", 1)
        if f"{method} {path}" in routes:
            continue
        # параметризованные пути ищем по маске сегментов (динамические {..} игнорируем)
        if not _path_variants_match(routes, method, path):
            missing.append(ep)
    assert not missing, f"Отсутствующие обязательные эндпоинты: {missing}"


def test_ai_answer_with_sources_top_level_registered():
    routes = _route_set()
    assert routes.get("POST /ai/answer_with_sources"), "POST /ai/answer_with_sources не зарегистрирован"

    # Обратная совместимость (старый путь) не должна пропадать
    assert routes.get("POST /kb/ai/answer_with_sources"), "POST /kb/ai/answer_with_sources отсутствует"


def test_ai_review_top_level_registered():
    routes = _route_set()
    assert routes.get("POST /ai/review"), "POST /ai/review не зарегистрирован"


# ─── Структура тестовых данных (fix-prompt §7) ────────────────────────────────
def _load_jsonl(path: Path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def test_specs_jsonl_has_10_and_needs_review_cases():
    p = TESTS_DATA / "specs" / "specs.jsonl"
    assert p.exists(), f"{p} отсутствует"
    specs = _load_jsonl(p)
    assert len(specs) == 10, f"ожидается 10 ТЗ, получено {len(specs)}"
    flagged = [s for s in specs if s.get("expected_needs_review") is True]
    assert len(flagged) >= 2, "минимум 2 теста должны приводить к needs_review=true"
    # противоречивые должны содержать high-риск ожидание
    contradictory = [s for s in specs if s.get("expected_high_risk")]
    assert len(contradictory) >= 1, "не найден противоречивый тест с ожиданием high-риска"


def test_kb_documents_has_5():
    p = TESTS_DATA / "kb_documents.jsonl"
    assert p.exists(), f"{p} отсутствует"
    docs = _load_jsonl(p)
    assert len(docs) == 5, f"ожидается 5 документов БЗ, получено {len(docs)}"
    for d in docs:
        assert d["title"] and d["text"], f"документ без title/text: {d.get('title')}"


def test_kb_questions_distribution():
    p = TESTS_DATA / "kb_questions.jsonl"
    assert p.exists(), f"{p} отсутствует"
    qs = _load_jsonl(p)
    assert len(qs) == 10, f"ожидается 10 вопросов, получено {len(qs)}"
    with_answer = [q for q in qs if q.get("expected_needs_review") is False]
    no_answer = [q for q in qs if q.get("expected_needs_review") is True]
    assert len(with_answer) == 7, f"ожидается 7 вопросов с ответом, получено {len(with_answer)}"
    assert len(no_answer) == 3, f"ожидается 3 вопроса без ответа, получено {len(no_answer)}"


# ─── Лимиты валидации (fix-prompt §3 / Option2 §1) ───────────────────────────
def test_document_create_length_limit():
    from app.schemas import DocumentCreate
    from annotated_types import MaxLen, MinLen
    field = DocumentCreate.model_fields["text"]
    mlen = [m for m in field.metadata if isinstance(m, MaxLen)]
    mnlen = [m for m in field.metadata if isinstance(m, MinLen)]
    assert mlen and mlen[0].max_length == 30_000, f"ожидается max 30 000, получено {mlen}"
    assert mnlen, "text должен иметь нижнюю границу длины (min)"
    assert mnlen[0].min_length == 10, f"ожидается min 10, получено {mnlen[0].min_length}"