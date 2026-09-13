"""
KB Auto-index — Фаза 3: сгенерированные артефакты (URS/SRS/ADR/диаграммы) и уроки проекта
(ProjectLesson) автоматически попадают в базу знаний команды, чтобы следующий цикл
рецензии/генерации диаграмм мог опираться на "как делали в прошлый раз" через /kb/ask.

Механизм: создаём KBDocument (таблица kb_documents, Вариант 5 — та же сущность, что и обычные
KB-статьи, уже видна в разделе "Документы" веб-панели и участвует в reindex), индексируем его
через rag_engine.index_document() (те же KBSnippet-и, тот же гибридный поиск). Ничего нового
изобретать не пришлось — только правильно дёрнуть уже существующий механизм в новых точках.

source_type/source_id на KBDocument — provenance: откуда взялась статья (не теряем связь
с оригинальным URS/SRS/ADR/набором диаграмм).

Побочный эффект намеренно НЕ должен ронять основной запрос (генерацию URS и т.п.) — обёрнуто
в try/except с логированием, а не пробрасыванием исключения наверх.
"""
import json
import logging
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kb_document import KBDocument
from app.services import rag_engine

logger = logging.getLogger(__name__)

MAX_KB_TEXT_LEN = 20_000


async def autoindex_artifact(
    db: AsyncSession,
    *,
    title: str,
    text: str,
    source_type: str,
    source_id: str,
    project_name: str | None = None,
) -> KBDocument | None:
    """Создаёт KBDocument из готового текста и индексирует его для RAG.
    Возвращает None, если индексировать нечего (пустой текст) — не считается ошибкой."""
    if not text or not text.strip():
        return None
    try:
        doc = KBDocument(
            id=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            title=f"[Авто] {title}"[:500],
            text=text[:MAX_KB_TEXT_LEN],
            project_name=project_name,
            source_type=source_type,
            source_id=source_id,
        )
        db.add(doc)
        await db.flush()
        await rag_engine.index_document(db, doc.id, doc.text)
        return doc
    except Exception as e:
        # Индексация в KB — побочный эффект генерации артефакта, а не её цель.
        # Падение здесь не должно ломать основной ответ пользователю.
        logger.warning("KB autoindex failed for %s/%s: %s", source_type, source_id, e)
        return None


# ── Текстовые сборщики: превращают структурированный JSON артефакта в осмысленный текст ──
# для поиска (RAG работает по тексту, а не по JSON-полям).

def urs_to_text(data: dict, title: str = "") -> str:
    lines = [f"URS: {data.get('title') or title}", f"Цель: {data.get('objective', '')}"]
    if data.get("stakeholders"):
        lines.append("Стейкхолдеры: " + ", ".join(data["stakeholders"]))
    for req in data.get("user_requirements", []):
        if isinstance(req, dict):
            lines.append(f"- [{req.get('id', '')}] {req.get('description', '')} (приоритет: {req.get('priority', '')})")
    for nfr in data.get("non_functional_requirements", []):
        if isinstance(nfr, dict):
            lines.append(f"- НФТ [{nfr.get('id', '')}] {nfr.get('category', '')}: {nfr.get('description', '')}")
    if data.get("constraints"):
        lines.append("Ограничения: " + "; ".join(data["constraints"]))
    return "\n".join(lines)


def srs_to_text(data: dict, title: str = "") -> str:
    lines = [f"SRS: {data.get('title') or title}", data.get("introduction", ""), data.get("overall_description", "")]
    for fr in data.get("functional_requirements", []):
        if isinstance(fr, dict):
            lines.append(f"- [{fr.get('id', '')}] {fr.get('description', '')} (приоритет: {fr.get('priority', '')})")
    for nfr in data.get("non_functional_requirements", []):
        if isinstance(nfr, dict):
            lines.append(f"- НФТ [{nfr.get('id', '')}] {nfr.get('category', '')}: {nfr.get('description', '')}")
    if data.get("external_interfaces"):
        lines.append("Внешние интерфейсы: " + "; ".join(data["external_interfaces"]))
    return "\n".join(l for l in lines if l)


def adr_to_text(data: dict, title: str = "") -> str:
    lines = [f"ADR: {data.get('title') or title}", f"Статус: {data.get('status', '')}"]
    for key in ("context", "problem", "decision"):
        if data.get(key):
            lines.append(f"{key}: {data[key]}")
    for alt in data.get("alternatives", []):
        if isinstance(alt, dict):
            lines.append(f"Альтернатива: {alt.get('option', '')} — отклонена: {alt.get('reason_rejected', '')}")
    consequences = data.get("consequences") or {}
    if isinstance(consequences, dict):
        if consequences.get("positive"):
            lines.append("Плюсы: " + "; ".join(consequences["positive"]))
        if consequences.get("negative"):
            lines.append("Минусы: " + "; ".join(consequences["negative"]))
    return "\n".join(lines)


def diagrams_to_text(diagram_map: dict, title: str, standard: str) -> str:
    lines = [f"Диаграммы для «{title}» (стандарт: {standard})"]
    for dtype, (notation, code) in diagram_map.items():
        if not code:
            continue
        # Не весь код диаграммы, а осмысленная выжимка — заголовок/первые строки достаточно
        # для поиска "как называли компоненты в прошлый раз", не раздувая KB полными дампами.
        snippet = "\n".join(code.splitlines()[:12])
        lines.append(f"\n--- {dtype} ({notation}) ---\n{snippet}")
    return "\n".join(lines)


def lesson_to_text(title: str, description: str, category: str, impact_type: str,
                    root_cause: str | None, recommendation: str | None) -> str:
    lines = [f"Урок проекта: {title}", f"Категория: {category}, влияние: {impact_type}", description]
    if root_cause:
        lines.append(f"Первопричина: {root_cause}")
    if recommendation:
        lines.append(f"Рекомендация на будущее: {recommendation}")
    return "\n".join(l for l in lines if l)
