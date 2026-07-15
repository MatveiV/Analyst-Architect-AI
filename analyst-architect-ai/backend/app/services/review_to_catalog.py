"""
Auto-populate RiskCatalogItem and ProjectLesson from review JSON.
"""
import json
import uuid
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.risk_catalog import RiskCatalogItem
from app.models.project_lesson import ProjectLesson
from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

# Map review severity -> (probability, impact) defaults
SEVERITY_MAP = {
    "low": (2, 2),
    "medium": (3, 2),
    "high": (4, 3),
}


def _severity_to_pi(severity: str) -> tuple[int, int]:
    return SEVERITY_MAP.get(severity.lower(), (1, 1))


async def store_risks_from_review(
    db: AsyncSession,
    review_json_str: str,
    document_id: str,
    project_name: Optional[str] = None,
) -> int:
    """Parse risks from review JSON and create RiskCatalogItem records."""
    try:
        data = json.loads(review_json_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Cannot parse review JSON for risk extraction")
        return 0

    risks = data.get("risks", [])
    count = 0
    for r in risks:
        desc = r.get("description", "").strip()
        if not desc:
            continue
        sev = r.get("severity", "medium")
        prob, imp = _severity_to_pi(sev)
        item = RiskCatalogItem(
            id=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            project_name=project_name,
            title=desc[:200],
            description=desc,
            probability=prob,
            impact=imp,
            category="tech",
            status="open",
            owner=None,
            mitigation=None,
            document_id=document_id,
            source="review",
        )
        db.add(item)
        count += 1
    if count:
        await db.commit()
    return count


_LESSON_PROMPT = """You are a structured-data extractor. Given a lessons-learned sentence,
produce valid JSON with these fields:
- title: short summary (max 200 chars)
- description: same sentence (max 2000 chars)
- category: one of "technology", "process", "communication", "estimation"
- impact_type: "positive" or "negative"
- root_cause: what caused this (string, max 1000 chars)
- recommendation: how to address it (string, max 1000 chars)

Input: {lesson_text}
JSON:"""


async def parse_lesson_with_llm(lesson_text: str) -> dict:
    """Use LLM to parse a free-text lesson into structured fields."""
    try:
        prompt = _LESSON_PROMPT.format(lesson_text=lesson_text[:2000])
        response = await call_llm(prompt, max_tokens=600)

        # Try to find JSON in the response
        content = response.strip()
        # Use the extract_json logic similar to llm_client
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if match:
            content = match.group(1)
        else:
            brace_start = content.find("{")
            brace_end = content.rfind("}")
            if brace_start != -1 and brace_end > brace_start:
                content = content[brace_start:brace_end + 1]
            else:
                raise ValueError("No JSON found in LLM response")
        parsed = json.loads(content)
        return {
            "title": str(parsed.get("title", lesson_text[:200])),
            "description": str(parsed.get("description", lesson_text)),
            "category": str(parsed.get("category", "process")),
            "impact_type": str(parsed.get("impact_type", "negative")),
            "root_cause": str(parsed.get("root_cause", "")),
            "recommendation": str(parsed.get("recommendation", "")),
        }
    except Exception as e:
        logger.warning(f"LLM parsing failed for lesson, using defaults: {e}")
        return {
            "title": lesson_text[:200],
            "description": lesson_text,
            "category": "process",
            "impact_type": "negative",
            "root_cause": "",
            "recommendation": "",
        }


async def store_lessons_from_review(
    db: AsyncSession,
    review_json_str: str,
    document_id: str,
    project_name: Optional[str] = None,
) -> int:
    """Parse lessons_learned from review JSON and create ProjectLesson records."""
    try:
        data = json.loads(review_json_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Cannot parse review JSON for lesson extraction")
        return 0

    lessons = data.get("lessons_learned", [])
    count = 0
    for lesson_text in lessons:
        if not isinstance(lesson_text, str) or not lesson_text.strip():
            continue
        parsed = await parse_lesson_with_llm(lesson_text)
        # Validate category
        cat = parsed["category"]
        if cat not in ("technology", "process", "communication", "estimation"):
            cat = "process"
        imp_type = parsed["impact_type"]
        if imp_type not in ("positive", "negative"):
            imp_type = "negative"

        item = ProjectLesson(
            id=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            project_name=project_name,
            title=parsed["title"][:200],
            description=parsed["description"],
            category=cat,
            impact_type=imp_type,
            root_cause=parsed.get("root_cause") or None,
            recommendation=parsed.get("recommendation") or None,
            document_id=document_id,
            source="review",
        )
        db.add(item)
        count += 1
    if count:
        await db.commit()
    return count
