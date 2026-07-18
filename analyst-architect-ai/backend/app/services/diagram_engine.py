"""
Diagram Engine — генерация PlantUML и Mermaid диаграмм.
Генерирует набор: C4 (Context/Container/Component), UML (Use Case, Sequence, Class, ERD), Mermaid Flowchart.

Эпик A1/A2: локальный рендер через Kroki вместо публичных plantuml.com/mermaid.live.
Эпик B4: набор и структура диаграмм зависят от выбранного пользователем стандарта.
Эпик C5: при ENFORCE_LOCAL_ONLY рендер не уходит во внешний сервис при недоступности Kroki.
"""
import json
import httpx
from pydantic import ValidationError
from app.config import settings
from app.schemas import DiagramSetSchema
from app.services.llm_client import call_llm, extract_json

# ── Эпик A1/A2: локальный рендер диаграмм ────────────────────────────────────

KROKI_NOTATION_MAP = {"plantuml": "plantuml", "mermaid": "mermaid"}


async def render_diagram(source_code: str, notation: str) -> dict:
    """
    Рендерит диаграмму локально через Kroki (svg + png).
    Возвращает {"render_svg": str|None, "render_png": bytes|None,
                "render_status": "ok"|"failed"|"external_fallback"|"blocked_external",
                "render_error": str|None}.

    Эпик C5: если Kroki недоступен и settings.ENFORCE_LOCAL_ONLY=True — НЕ уходим на внешний
    рендер-сервис (plantuml.com/mermaid.live), а честно возвращаем blocked_external.
    """
    kroki_notation = KROKI_NOTATION_MAP.get(notation)
    if not kroki_notation:
        return {"render_svg": None, "render_png": None, "render_status": "failed",
                "render_error": f"Неизвестная нотация: {notation}"}

    base = settings.DIAGRAM_RENDERER_URL.rstrip("/")
    timeout = settings.DIAGRAM_RENDERER_TIMEOUT

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            svg_resp = await client.post(
                f"{base}/{kroki_notation}/svg",
                content=source_code.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
            png_resp = await client.post(
                f"{base}/{kroki_notation}/png",
                content=source_code.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
        if svg_resp.status_code == 200 and png_resp.status_code == 200:
            return {
                "render_svg": svg_resp.text,
                "render_png": png_resp.content,
                "render_status": "ok",
                "render_error": None,
            }
        return {"render_svg": None, "render_png": None, "render_status": "failed",
                "render_error": f"Kroki вернул {svg_resp.status_code}/{png_resp.status_code}"}
    except Exception as e:
        if settings.ENFORCE_LOCAL_ONLY:
            # Локальный контур обязателен — не уходим во внешний рендер молча.
            return {
                "render_svg": None, "render_png": None,
                "render_status": "blocked_external",
                "render_error": (
                    "Локальный рендер-сервис (Kroki) недоступен, а ENFORCE_LOCAL_ONLY=true "
                    "запрещает уход во внешний сервис. Проверьте, что сервис kroki запущен."
                ),
            }
        # Локальный контур не требуется — можно отрендерить фронтенду через публичный сервис
        # (см. DiagramViewer.tsx: PlantUMLDiagram/MermaidDiagram уже умеют это делать сами).
        return {
            "render_svg": None, "render_png": None,
            "render_status": "external_fallback",
            "render_error": f"Kroki недоступен ({e}); диаграмма будет отрендерена во внешнем сервисе на фронтенде",
        }

DIAGRAM_SYSTEM = """Ты — архитектор и технический аналитик. Генерируй диаграммы на основе требований.

Правила:
- Для PlantUML: начинай каждую диаграмму с @startuml и заканчивай @enduml
- Для Mermaid: используй стандартный синтаксис (flowchart LR, sequenceDiagram и т.д.)
- Диаграммы должны отражать реальные сущности из документа
- Возвращай строгий JSON без Markdown-обёртки

Формат:
{
  "c4_context": "PlantUML код C4 Context",
  "c4_container": "PlantUML код C4 Container",
  "c4_component": "PlantUML код C4 Component",
  "use_case": "PlantUML Use Case диаграмма",
  "sequence": "PlantUML Sequence диаграмма",
  "class_diagram": "PlantUML Class диаграмма",
  "erd": "PlantUML ERD диаграмма",
  "mermaid_flowchart": "Mermaid flowchart",
  "confidence": "high|medium|low",
  "needs_review": false
}"""

SINGLE_DIAGRAM_SYSTEM = """Ты — архитектор. Генерируй одну диаграмму на основе требований.
Для PlantUML: начинай с @startuml и заканчивай @enduml.
Возвращай ТОЛЬКО код диаграммы, без пояснений."""


def _fallback_c4(title: str = "System") -> str:
    return f"""@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml
title System Context — {title}
Person(user, "Пользователь", "Использует систему")
System(system, "{title}", "Основная система")
Rel(user, system, "Использует")
@enduml"""


def _fallback_mermaid(title: str = "System") -> str:
    return f"""flowchart LR
    User([Пользователь]) --> System[{title}]
    System --> DB[(База данных)]
    System --> API[Внешний API]"""


def safe_fallback_diagrams(title: str = "System") -> DiagramSetSchema:
    return DiagramSetSchema(
        c4_context=_fallback_c4(title),
        c4_container="@startuml\ntitle Container Diagram\nnote: Требует ручного заполнения\n@enduml",
        c4_component="@startuml\ntitle Component Diagram\nnote: Требует ручного заполнения\n@enduml",
        use_case="@startuml\ntitle Use Case\nactor User\nusecase UC1 as \"Основной сценарий\"\nUser --> UC1\n@enduml",
        sequence="@startuml\ntitle Sequence\nactor User\nparticipant System\nUser -> System: Запрос\nSystem --> User: Ответ\n@enduml",
        class_diagram="@startuml\ntitle Class Diagram\nclass Entity {}\n@enduml",
        erd="@startuml\ntitle ERD\nentity Entity {}\n@enduml",
        mermaid_flowchart=_fallback_mermaid(title),
        confidence="low",
        needs_review=True,
    )


# ── Эпик B4: наборы диаграмм по стандарту ────────────────────────────────────
# Стандарты, для которых автогенерация — это приближение, требующее ручной сверки обозначений.
APPROXIMATE_DIAGRAM_STANDARDS = {"GOST_19_701", "IEC_61082"}

STANDARD_DIAGRAM_INSTRUCTIONS = {
    "C4_MODEL": "Строй диаграммы строго по C4-модели: Context, Container, Component (+Code при необходимости).",
    "UML_ISO_19505": "Строй диаграммы по UML (ISO/IEC 19505): Use Case, Sequence, Class, State, Activity.",
    "ISO_IEC_IEEE_42010": (
        "Строй НЕ одну диаграмму, а комплект viewpoints по ISO/IEC/IEEE 42010: для каждого вида "
        "укажи interest стейкхолдера (stakeholder concern), которому он отвечает, в поле viewpoints."
    ),
    "GOST_19_701": (
        "Строй блок-схему алгоритма в терминологии ГОСТ 19.701-90 (блоки: процесс, решение, "
        "данные, начало/конец). Это приближение — обязательно верни confidence='low' и needs_review=true, "
        "т.к. точное соответствие форме блоков ГОСТ требует ручной проверки."
    ),
    "IEC_61082": (
        "IEC 61082 — стандарт оформления инженерной/электротехнической документации, для чисто "
        "программных систем применим ограниченно. Построй функциональную схему по аналогии, но "
        "обязательно верни confidence='low' и needs_review=true."
    ),
}


async def generate_all_diagrams(
    document_text: str,
    title: str = "System",
    project_context: str = "",
    standard: str = "C4_MODEL",
) -> DiagramSetSchema:
    instruction = STANDARD_DIAGRAM_INSTRUCTIONS.get(standard, STANDARD_DIAGRAM_INSTRUCTIONS["C4_MODEL"])
    prompt = f"""Создай набор диаграмм для следующей системы.
Заголовок: {title}
Стандарт: {standard}. {instruction}

Требования:
{document_text[:5000]}
{project_context[:1500]}
Сгенерируй все диаграммы и верни строгий JSON."""

    try:
        raw = await call_llm(prompt, DIAGRAM_SYSTEM)
        clean = extract_json(raw)
        data = json.loads(clean)
        schema = DiagramSetSchema(**data)
        schema.standard_profile = standard

        # Validate PlantUML starts/ends correctly
        plantuml_fields = ["c4_context", "c4_container", "c4_component", "use_case", "sequence", "class_diagram", "erd"]
        for field in plantuml_fields:
            val = getattr(schema, field, "")
            if val and "@startuml" not in val:
                setattr(schema, field, f"@startuml\n{val}\n@enduml")

        # Честная оговорка для приближённых стандартов — не выдаём approximation за 100% соответствие
        if standard in APPROXIMATE_DIAGRAM_STANDARDS:
            schema.confidence = "low"
            schema.needs_review = True

        return schema
    except Exception:
        result = safe_fallback_diagrams(title)
        result.standard_profile = standard
        return result


async def generate_c4_diagrams(document_text: str, title: str = "System") -> dict:
    prompt = f"""Создай три C4 диаграммы (Context, Container, Component) для системы "{title}".

Требования:
{document_text[:3000]}

Верни JSON с ключами c4_context, c4_container, c4_component (PlantUML код)."""

    try:
        raw = await call_llm(prompt, DIAGRAM_SYSTEM)
        clean = extract_json(raw)
        data = json.loads(clean)
        return {k: data.get(k, "") for k in ["c4_context", "c4_container", "c4_component"]}
    except Exception:
        return {
            "c4_context": _fallback_c4(title),
            "c4_container": f"@startuml\ntitle C4 Container — {title}\n@enduml",
            "c4_component": f"@startuml\ntitle C4 Component — {title}\n@enduml",
        }


async def generate_uml_diagrams(document_text: str) -> dict:
    prompt = f"""Создай UML диаграммы (Use Case, Sequence, Class, State, Activity) для:
{document_text[:3000]}

Верни JSON с ключами: use_case, sequence, class_diagram, state, activity (PlantUML код)."""

    try:
        raw = await call_llm(prompt, DIAGRAM_SYSTEM)
        clean = extract_json(raw)
        data = json.loads(clean)
        return {k: data.get(k, "") for k in ["use_case", "sequence", "class_diagram", "state", "activity"]}
    except Exception:
        return {
            "use_case": "@startuml\ntitle Use Case\nactor User\n@enduml",
            "sequence": "@startuml\ntitle Sequence\n@enduml",
            "class_diagram": "@startuml\ntitle Class Diagram\n@enduml",
            "state": "@startuml\ntitle State Diagram\n@enduml",
            "activity": "@startuml\ntitle Activity Diagram\n@enduml",
        }


async def generate_erd(document_text: str) -> str:
    prompt = f"""Создай ERD (Entity Relationship Diagram) в PlantUML для:
{document_text[:3000]}

Верни ТОЛЬКО PlantUML код, начинающийся с @startuml."""

    try:
        raw = await call_llm(prompt, SINGLE_DIAGRAM_SYSTEM)
        code = extract_json(raw)
        if "@startuml" not in code:
            code = f"@startuml\n{code}\n@enduml"
        return code
    except Exception:
        return "@startuml\ntitle ERD\nnote: Требует ручного заполнения\n@enduml"
