"""
Document Generator — генерация URS, SRS и OpenAPI спецификаций.
"""
import json
import yaml
from pydantic import ValidationError
from app.schemas import URSSchema, SRSSchema
from app.services.llm_client import call_llm, extract_json

URS_SYSTEM = """Ты — Lead System Analyst. Создай URS (User Requirements Specification) на основе ТЗ.

Формат строгий JSON:
{
  "title": "string",
  "objective": "string",
  "stakeholders": ["string"],
  "user_requirements": [{"id": "UR-001", "description": "string", "priority": "high|medium|low"}],
  "non_functional_requirements": [{"id": "NFR-001", "category": "string", "description": "string"}],
  "constraints": ["string"],
  "confidence": "high|medium|low",
  "needs_review": false
}"""

SRS_SYSTEM = """Ты — Lead System Analyst. Создай SRS (Software Requirements Specification) на основе ТЗ.

Формат строгий JSON:
{
  "title": "string",
  "introduction": "string",
  "overall_description": "string",
  "functional_requirements": [{"id": "FR-001", "description": "string", "priority": "high|medium|low"}],
  "non_functional_requirements": [{"id": "NFR-001", "category": "string", "description": "string"}],
  "external_interfaces": ["string"],
  "confidence": "high|medium|low",
  "needs_review": false
}"""

API_SYSTEM = """Ты — API Architect. Создай OpenAPI 3.1 спецификацию на основе требований.

Возвращай строгий JSON (OpenAPI 3.1 объект) без Markdown-обёртки.
Включи: info, paths (минимум 3-5 эндпоинтов), components/schemas."""


def _safe_urs_fallback() -> URSSchema:
    return URSSchema(
        title="URS: Требует ручного заполнения",
        objective="Не удалось автоматически сформировать URS",
        confidence="low",
        needs_review=True,
    )


def _safe_srs_fallback() -> SRSSchema:
    return SRSSchema(
        title="SRS: Требует ручного заполнения",
        introduction="Не удалось автоматически сформировать SRS",
        confidence="low",
        needs_review=True,
    )


async def generate_urs(document_text: str, title: str = "", project_context: str = "") -> URSSchema:
    prompt = f"""Создай URS для следующего ТЗ:
Название: {title}

{document_text}
{project_context}
Верни строгий JSON."""
    try:
        raw = await call_llm(prompt, URS_SYSTEM)
        clean = extract_json(raw)
        data = json.loads(clean)
        return URSSchema(**data)
    except Exception:
        return _safe_urs_fallback()


async def generate_srs(document_text: str, title: str = "", project_context: str = "") -> SRSSchema:
    prompt = f"""Создай SRS для следующего ТЗ:
Название: {title}

{document_text}
{project_context}
Верни строгий JSON."""
    try:
        raw = await call_llm(prompt, SRS_SYSTEM)
        clean = extract_json(raw)
        data = json.loads(clean)
        return SRSSchema(**data)
    except Exception:
        return _safe_srs_fallback()


async def generate_api_spec(document_text: str, title: str = "", project_context: str = "") -> tuple[str, str]:
    """Returns (json_str, yaml_str) for OpenAPI spec."""
    prompt = f"""Создай OpenAPI 3.1 спецификацию для системы "{title}".

Требования:
{document_text[:4000]}
{project_context[:1000]}
Верни валидный OpenAPI 3.1 JSON объект."""

    try:
        raw = await call_llm(prompt, API_SYSTEM)
        clean = extract_json(raw)
        data = json.loads(clean)
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        yaml_str = yaml.dump(data, allow_unicode=True, default_flow_style=False)
        return json_str, yaml_str
    except Exception:
        fallback = {
            "openapi": "3.1.0",
            "info": {"title": title or "API", "version": "0.1.0"},
            "paths": {},
        }
        return json.dumps(fallback, indent=2), yaml.dump(fallback)
