"""
AI Reviewer — AI-рецензент технических заданий.
Строгий JSON output, safe fallback при ошибке LLM.
"""
import json
from pydantic import ValidationError
from app.schemas import ReviewSchema, RiskItem
from app.services.llm_client import call_llm, extract_json

REVIEW_SYSTEM = """Ты — Senior System Analyst с 15 годами опыта. Твоя задача — провести экспертную рецензию технического задания.

ПРАВИЛА:
1. Никогда не выдумывай факты, которых нет в документе.
2. Если документ слишком короткий или противоречивый — это риск, ставь confidence="low".
3. Вопросы заказчику должны снимать реальную неопределённость.
4. Критерии приёмки должны быть проверяемыми (тестируемыми).
5. Всегда возвращай строгий JSON без Markdown-обёртки, без пояснений.

Строгий JSON формат ответа:
{
  "summary": "string",
  "risks": [{"severity": "low|medium|high", "description": "string"}],
  "missing_requirements": ["string"],
  "questions_to_client": ["string"],
  "acceptance_criteria": ["string"],
  "similar_projects": ["string"],
  "lessons_learned": ["string"],
  "related_decisions": ["string"],
  "architecture_risks": ["string"],
  "confidence": "high|medium|low",
  "needs_review": false
}"""

# ── Reasoning modes (перенесено из MatveiV/Analyst-Guru) ─────────────────────
# "direct" — прямой вызов без явного рассуждения (по умолчанию, самый быстрый/дешёвый)
# "cot"    — Chain-of-Thought: модель сначала рассуждает по шагам, затем выдаёт JSON
# "react"  — ReAct: модель чередует Thought/Action/Observation перед выводом JSON
#
# В обоих режимах рассуждение выполняется в том же вызове (не требует доп. раунда),
# а извлекается только финальный JSON-блок — цена быстрее и прозрачнее, чем агентные
# циклы с реальными инструментами.

COT_INSTRUCTION = """
Прежде чем сформировать JSON, распиши ход рассуждений по шагам в отдельном блоке
<thinking>...</thinking> (кратко, 5-8 шагов): что понятно, что рискованно, какие
вопросы логично задать. После блока <thinking> выведи ИСКЛЮЧИТЕЛЬНО финальный JSON."""

REACT_INSTRUCTION = """
Используй цикл ReAct перед финальным JSON, в блоке <reasoning>...</reasoning>:
Thought: что нужно проверить в документе
Action: проверить [конкретный аспект: полноту требований / противоречия / критерии]
Observation: что обнаружено
(повтори Thought/Action/Observation 2-4 раза для ключевых аспектов документа)
После блока <reasoning> выведи ИСКЛЮЧИТЕЛЬНО финальный JSON, без Markdown-обёртки."""


def _system_prompt_for_mode(reasoning_mode: str) -> str:
    if reasoning_mode == "cot":
        return REVIEW_SYSTEM + "\n" + COT_INSTRUCTION
    if reasoning_mode == "react":
        return REVIEW_SYSTEM + "\n" + REACT_INSTRUCTION
    return REVIEW_SYSTEM


def _strip_reasoning_blocks(raw: str) -> str:
    """Remove <thinking>/<reasoning> blocks before JSON extraction (CoT/ReAct modes)."""
    import re
    raw = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"<reasoning>.*?</reasoning>", "", raw, flags=re.DOTALL)
    return raw.strip()


def _detect_contradiction(text: str) -> bool:
    """Heuristic: detect obvious contradictions in short documents."""
    contradiction_pairs = [
        ("авторизация не нужна", "авторизация"),
        ("не хранить", "хранить"),
        ("24/7", "требует постоянного присутствия оператора"),
        ("мгновенно", "согласовывать"),
    ]
    text_lower = text.lower()
    for pair in contradiction_pairs:
        if all(p in text_lower for p in pair):
            return True
    return False


def _is_too_vague(text: str) -> bool:
    return len(text.strip()) < 50 or len(text.strip().split()) < 8


def safe_fallback_review(error: str = "INVALID_JSON", reason: str = "") -> ReviewSchema:
    return ReviewSchema(
        summary="Не удалось автоматически проанализировать документ. Требуется ручная проверка.",
        risks=[RiskItem(severity="high", description=f"Ошибка анализа: {error}. {reason}")],
        missing_requirements=["Не удалось извлечь из-за ошибки формата"],
        questions_to_client=[
            "Пожалуйста, уточните требования у заказчика",
            "Предоставьте более детальное описание задачи",
            "Опишите ожидаемый результат и критерии успеха",
        ],
        acceptance_criteria=[],
        confidence="low",
        needs_review=True,
    )


async def run_ai_review(
    text: str,
    memory_risks: str = "",
    memory_lessons: str = "",
    memory_decisions: str = "",
    reasoning_mode: str = "direct",
) -> ReviewSchema:
    # Pre-validation
    if _is_too_vague(text):
        return ReviewSchema(
            summary="Документ слишком краткий для полноценного анализа.",
            risks=[RiskItem(severity="high", description="TOO_VAGUE_INPUT: документ содержит менее 8 слов")],
            missing_requirements=["Весь документ требует детализации"],
            questions_to_client=[
                "Что именно нужно сделать?",
                "Кто будет пользователями системы?",
                "Каков ожидаемый результат?",
                "Каковы сроки и бюджет?",
            ],
            acceptance_criteria=[],
            confidence="low",
            needs_review=True,
        )

    # Build prompt
    context_block = ""
    if memory_risks:
        context_block += f"\nИзвестные риски из памяти: {memory_risks}"
    if memory_lessons:
        context_block += f"\nУроки проектов: {memory_lessons}"
    if memory_decisions:
        context_block += f"\nСвязанные решения: {memory_decisions}"

    prompt = f"""Проведи экспертную рецензию следующего технического задания:{context_block}

ДОКУМЕНТ:
{text}

Верни строгий JSON без Markdown-обёртки."""

    system_prompt = _system_prompt_for_mode(reasoning_mode)

    try:
        raw = await call_llm(prompt, system_prompt)
        raw = _strip_reasoning_blocks(raw)
        clean = extract_json(raw)
        if not clean:
            return safe_fallback_review("INVALID_JSON", "LLM вернул пустой ответ")
        data = json.loads(clean, strict=False)
        schema = ReviewSchema(**data)

        # Post-validation: detect contradictions
        if _detect_contradiction(text) and schema.confidence != "low":
            schema.confidence = "low"
            schema.needs_review = True
            schema.risks.append(RiskItem(
                severity="high",
                description="CONTRADICTORY_INPUT: обнаружены противоречия в требованиях"
            ))

        return schema

    except (json.JSONDecodeError, ValidationError) as e:
        return safe_fallback_review("INVALID_JSON", str(e)[:200])
    except Exception as e:
        return safe_fallback_review("LLM_ERROR", str(e)[:200])
