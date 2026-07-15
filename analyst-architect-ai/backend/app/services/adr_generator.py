"""ADR Generator — Architecture Decision Record."""
import json
from pydantic import ValidationError
from app.schemas import ADRSchema, ADRConsequences
from app.services.llm_client import call_llm, extract_json

ADR_SYSTEM = """Ты — Lead Architect. Создай Architecture Decision Record (ADR) на основе предоставленных требований.

ADR документирует архитектурное решение: контекст, проблему, принятое решение, альтернативы и последствия.

Формат строгий JSON без Markdown-обёртки:
{
  "title": "ADR-NNN: Название решения",
  "status": "proposed|accepted",
  "context": "Контекст принятия решения",
  "problem": "Формулировка проблемы",
  "decision": "Принятое решение",
  "alternatives": [{"option": "string", "reason_rejected": "string"}],
  "consequences": {"positive": ["string"], "negative": ["string"]},
  "confidence": "high|medium|low",
  "needs_review": false
}"""


def safe_fallback_adr() -> ADRSchema:
    return ADRSchema(
        title="ADR: Требует ручного оформления",
        status="proposed",
        context="Не удалось автоматически сформировать ADR",
        problem="Недостаточно данных для анализа",
        decision="Требует ручного заполнения",
        alternatives=[],
        consequences=ADRConsequences(positive=[], negative=["Требует ручной работы аналитика"]),
        confidence="low",
        needs_review=True,
    )


async def generate_adr(document_text: str, project_context: str = "") -> ADRSchema:
    prompt = f"""Создай ADR для следующих требований:

{document_text}
{project_context}
Верни строгий JSON."""

    try:
        raw = await call_llm(prompt, ADR_SYSTEM)
        clean = extract_json(raw)
        data = json.loads(clean)
        return ADRSchema(**data)
    except Exception:
        return safe_fallback_adr()
