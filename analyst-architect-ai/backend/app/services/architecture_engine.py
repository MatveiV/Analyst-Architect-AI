"""
Architecture Recommendation Engine.
Recommends architectural pattern based on document requirements.
"""
import json
from pydantic import ValidationError
from app.schemas import ArchitectureRecommendationSchema, RiskItem
from app.services.llm_client import call_llm, extract_json

ARCH_SYSTEM = """Ты — Solution Architect с 15+ годами опыта. Проанализируй требования и порекомендуй архитектурный паттерн.

Учитывай:
- Масштаб системы (нагрузка, команда, сложность)
- Зрелость команды
- Временны́е ограничения
- NFR (нефункциональные требования)

Паттерны: Monolith, Modular Monolith, Microservices, Event-Driven, CQRS, Serverless, Hexagonal.
Возвращай строгий JSON без Markdown-обёртки.

Формат:
{
  "recommended_pattern": "string",
  "rationale": "string",
  "alternatives": [{"pattern": "string", "pros": ["string"], "cons": ["string"]}],
  "integration_recommendations": ["REST|Kafka|gRPC|..."],
  "risks": [{"severity": "low|medium|high", "description": "string"}],
  "confidence": "high|medium|low",
  "needs_review": false
}"""


def safe_fallback_arch() -> ArchitectureRecommendationSchema:
    return ArchitectureRecommendationSchema(
        recommended_pattern="Modular Monolith",
        rationale="Не удалось проанализировать требования. Рекомендован Modular Monolith как универсальный безопасный выбор.",
        alternatives=[],
        integration_recommendations=["REST"],
        risks=[RiskItem(severity="high", description="Рекомендация сгенерирована без полного анализа требований")],
        confidence="low",
        needs_review=True,
    )


async def recommend_architecture(document_text: str, project_context: str = "") -> ArchitectureRecommendationSchema:
    prompt = f"""Проанализируй требования и порекомендуй архитектурный паттерн.

Документ с требованиями:
{document_text}
{project_context}
Верни строгий JSON."""

    try:
        raw = await call_llm(prompt, ARCH_SYSTEM)
        clean = extract_json(raw)
        data = json.loads(clean)
        return ArchitectureRecommendationSchema(**data)
    except (json.JSONDecodeError, ValidationError, Exception):
        return safe_fallback_arch()
