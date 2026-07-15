"""
Diagram Engine — генерация PlantUML и Mermaid диаграмм.
Генерирует набор: C4 (Context/Container/Component), UML (Use Case, Sequence, Class, ERD), Mermaid Flowchart.
"""
import json
from pydantic import ValidationError
from app.schemas import DiagramSetSchema
from app.services.llm_client import call_llm, extract_json

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


async def generate_all_diagrams(document_text: str, title: str = "System", project_context: str = "") -> DiagramSetSchema:
    prompt = f"""Создай набор диаграмм для следующей системы.
Заголовок: {title}

Требования:
{document_text[:5000]}
{project_context[:1500]}
Сгенерируй все диаграммы и верни строгий JSON."""

    try:
        raw = await call_llm(prompt, DIAGRAM_SYSTEM)
        clean = extract_json(raw)
        data = json.loads(clean)
        schema = DiagramSetSchema(**data)

        # Validate PlantUML starts/ends correctly
        plantuml_fields = ["c4_context", "c4_container", "c4_component", "use_case", "sequence", "class_diagram", "erd"]
        for field in plantuml_fields:
            val = getattr(schema, field, "")
            if val and "@startuml" not in val:
                setattr(schema, field, f"@startuml\n{val}\n@enduml")

        return schema
    except Exception:
        return safe_fallback_diagrams(title)


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
