"""
Document Generator — генерация URS, SRS и OpenAPI спецификаций.
Эпик B3: структура URS/SRS зависит от выбранного пользователем стандарта.
"""
import json
import yaml
from pydantic import ValidationError
from app.schemas import URSSchema, SRSSchema
from app.services.llm_client import call_llm, extract_json

# ── Эпик B3: обязательные разделы по стандарту ───────────────────────────────
# Стандарты, для которых автоматическая генерация — приближение (см. также diagram_engine.py)
APPROXIMATE_REQUIREMENTS_STANDARDS: set[str] = set()  # для requirements-стандартов пока нет приближённых

STANDARD_SECTION_MAP = {
    "urs": {
        "ISO_IEC_IEEE_29148": [
            "Scope", "Stakeholders and their needs", "User requirements",
            "Non-functional requirements", "Constraints",
        ],
        "IEEE_830": [
            "Introduction", "Overall description", "Specific requirements", "Constraints",
        ],
        "GOST_19": [
            "Введение", "Основания для разработки", "Назначение разработки",
            "Требования к программе", "Требования к программной документации",
        ],
        "GOST_34": [
            "Общие сведения", "Назначение и цели создания системы",
            "Требования к системе", "Состав и содержание работ по созданию системы",
            "Порядок контроля и приёмки",
        ],
    },
    "srs": {
        "ISO_IEC_IEEE_29148": [
            "Introduction", "Overall description", "Functional requirements",
            "Non-functional requirements", "External interfaces",
        ],
        "IEEE_830": [
            "Introduction", "Overall description", "Specific requirements",
            "External interface requirements",
        ],
        "GOST_19": [
            "Введение", "Основания для разработки", "Назначение разработки",
            "Требования к программе", "Требования к программной документации",
        ],
        "GOST_34": [
            "Общие сведения", "Назначение и цели создания системы",
            "Требования к системе", "Требования к видам обеспечения",
            "Состав и содержание работ по созданию системы",
        ],
    },
}


def _sections_for(doc_kind: str, standard: str) -> list[str]:
    mapping = STANDARD_SECTION_MAP[doc_kind]
    return mapping.get(standard, mapping["ISO_IEC_IEEE_29148"])


def _urs_system_for_standard(standard: str) -> str:
    sections = _sections_for("urs", standard)
    return f"""Ты — Lead System Analyst. Создай URS (User Requirements Specification) на основе ТЗ.
Структурируй строго по разделам стандарта {standard}: {", ".join(sections)}.
Если данных для обязательного раздела нет — оставь секцию пустой и добавь пункт в
missing_requirements с указанием, какого раздела не хватает; НЕ выдумывай содержание.

Формат строгий JSON:
{{
  "title": "string",
  "objective": "string",
  "stakeholders": ["string"],
  "user_requirements": [{{"id": "UR-001", "description": "string", "priority": "high|medium|low"}}],
  "non_functional_requirements": [{{"id": "NFR-001", "category": "string", "description": "string"}}],
  "constraints": ["string"],
  "missing_requirements": ["string"],
  "confidence": "high|medium|low",
  "needs_review": false
}}"""


def _srs_system_for_standard(standard: str) -> str:
    sections = _sections_for("srs", standard)
    return f"""Ты — Lead System Analyst. Создай SRS (Software Requirements Specification) на основе ТЗ.
Структурируй строго по разделам стандарта {standard}: {", ".join(sections)}.
Если данных для обязательного раздела нет — оставь секцию пустой и добавь пункт в
missing_requirements с указанием, какого раздела не хватает; НЕ выдумывай содержание.

Формат строгий JSON:
{{
  "title": "string",
  "introduction": "string",
  "overall_description": "string",
  "functional_requirements": [{{"id": "FR-001", "description": "string", "priority": "high|medium|low"}}],
  "non_functional_requirements": [{{"id": "NFR-001", "category": "string", "description": "string"}}],
  "external_interfaces": ["string"],
  "missing_requirements": ["string"],
  "confidence": "high|medium|low",
  "needs_review": false
}}"""


API_SYSTEM = """Ты — API Architect. Создай OpenAPI 3.1 спецификацию на основе требований.

Возвращай строгий JSON (OpenAPI 3.1 объект) без Markdown-обёртки.
Включи: info, paths (минимум 3-5 эндпоинтов), components/schemas."""


def _safe_urs_fallback(standard: str = "ISO_IEC_IEEE_29148") -> URSSchema:
    return URSSchema(
        title="URS: Требует ручного заполнения",
        objective="Не удалось автоматически сформировать URS",
        confidence="low",
        needs_review=True,
        standard_profile=standard,
    )


def _safe_srs_fallback(standard: str = "ISO_IEC_IEEE_29148") -> SRSSchema:
    return SRSSchema(
        title="SRS: Требует ручного заполнения",
        introduction="Не удалось автоматически сформировать SRS",
        confidence="low",
        needs_review=True,
        standard_profile=standard,
    )


async def generate_urs(
    document_text: str, title: str = "", project_context: str = "",
    standard: str = "ISO_IEC_IEEE_29148",
) -> URSSchema:
    system = _urs_system_for_standard(standard)
    prompt = f"""Создай URS для следующего ТЗ:
Название: {title}

{document_text}
{project_context}
Верни строгий JSON."""
    try:
        raw = await call_llm(prompt, system)
        clean = extract_json(raw)
        data = json.loads(clean)
        schema = URSSchema(**data)
        schema.standard_profile = standard
        if standard in APPROXIMATE_REQUIREMENTS_STANDARDS:
            schema.confidence = "low"
            schema.needs_review = True
        return schema
    except Exception:
        return _safe_urs_fallback(standard)


async def generate_srs(
    document_text: str, title: str = "", project_context: str = "",
    standard: str = "ISO_IEC_IEEE_29148",
) -> SRSSchema:
    system = _srs_system_for_standard(standard)
    prompt = f"""Создай SRS для следующего ТЗ:
Название: {title}

{document_text}
{project_context}
Верни строгий JSON."""
    try:
        raw = await call_llm(prompt, system)
        clean = extract_json(raw)
        data = json.loads(clean)
        schema = SRSSchema(**data)
        schema.standard_profile = standard
        if standard in APPROXIMATE_REQUIREMENTS_STANDARDS:
            schema.confidence = "low"
            schema.needs_review = True
        return schema
    except Exception:
        return _safe_srs_fallback(standard)


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
