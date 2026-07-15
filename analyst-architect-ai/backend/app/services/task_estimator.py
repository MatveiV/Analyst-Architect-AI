"""
Task Estimator — AI-декомпозиция требований на задачи с оценкой трудозатрат.
Используется экономическим модулем для расчёта CAPEX.
"""
import json
from pydantic import ValidationError
from app.schemas import TaskDecompositionSchema, TaskItem
from app.services.llm_client import call_llm, extract_json

TASK_ESTIMATOR_SYSTEM = """Ты — Senior Tech Lead с опытом оценки проектов. Разбей требования на задачи
и оцени трудозатраты по ролям: backend, frontend, qa, devops, analyst.

Правила:
1. Используй Story Points по шкале Фибоначчи (1, 2, 3, 5, 8, 13).
2. 1 story point ≈ 4 часа для опытной команды (используй как ориентир, но корректируй по сложности).
3. risk_multiplier: 1.0 (стандартно), 1.3 (есть неопределённость), 1.6 (высокий риск/новая технология).
4. Разбивай на 8-20 задач в зависимости от масштаба ТЗ.
5. Указывай реалистичные оценки, не занижай для сложных интеграций.

Строгий JSON без Markdown-обёртки:
{
  "tasks": [{"name": "string", "role": "backend|frontend|qa|devops|analyst", "story_points": 1, "estimated_hours": 4.0, "risk_multiplier": 1.0}],
  "total_hours_by_role": {"backend": 0, "frontend": 0, "qa": 0, "devops": 0, "analyst": 0},
  "confidence": "high|medium|low",
  "needs_review": false
}"""


def _safe_fallback_estimate() -> TaskDecompositionSchema:
    return TaskDecompositionSchema(
        tasks=[
            TaskItem(name="Требует ручной декомпозиции (анализ не удался)", role="analyst",
                     story_points=5, estimated_hours=20.0, risk_multiplier=1.3),
        ],
        total_hours_by_role={"analyst": 20.0},
        confidence="low",
        needs_review=True,
    )


def _recompute_totals(schema: TaskDecompositionSchema) -> TaskDecompositionSchema:
    """Recompute total_hours_by_role from individual tasks (defends against LLM arithmetic errors)."""
    totals: dict = {}
    for task in schema.tasks:
        hours = task.estimated_hours * (task.risk_multiplier or 1.0)
        totals[task.role] = totals.get(task.role, 0.0) + hours
    schema.total_hours_by_role = {k: round(v, 1) for k, v in totals.items()}
    return schema


async def estimate_tasks(document_text: str, project_name: str = "") -> TaskDecompositionSchema:
    prompt = f"""Требования проекта "{project_name}":

{document_text[:6000]}

Разбей на задачи и оцени трудозатраты. Верни строгий JSON."""

    try:
        raw = await call_llm(prompt, TASK_ESTIMATOR_SYSTEM)
        clean = extract_json(raw)
        data = json.loads(clean)
        schema = TaskDecompositionSchema(**data)
        if not schema.tasks:
            return _safe_fallback_estimate()
        return _recompute_totals(schema)
    except (json.JSONDecodeError, ValidationError, Exception):
        return _safe_fallback_estimate()
