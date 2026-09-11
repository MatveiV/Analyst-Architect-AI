"""
Memory Framework — хранение и поиск по 5 типам памяти:
semantic | episodic | decision | risk | requirement
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.memory_item import MemoryItem
from app.services.embeddings import (
    embed_text,
    keyword_score,
    hybrid_score,
    search_faiss,
    add_to_faiss_index,
)


async def store_memory(
    db: AsyncSession,
    memory_type: str,
    content: str,
    tags: List[str],
    project_name: Optional[str] = None,
) -> MemoryItem:
    emb = embed_text(content)
    item = MemoryItem(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        memory_type=memory_type,
        content=content,
        tags=json.dumps(tags, ensure_ascii=False),
        project_name=project_name,
        embedding=emb,
    )
    db.add(item)
    await db.commit()
    if emb:
        add_to_faiss_index(item.id, emb)
    return item


async def search_memory(
    db: AsyncSession,
    query: str,
    memory_type: Optional[str] = None,
    project_name: Optional[str] = None,
    limit: int = 10,
) -> List[MemoryItem]:
    q = select(MemoryItem)
    if memory_type:
        q = q.where(MemoryItem.memory_type == memory_type)
    if project_name:
        q = q.where(MemoryItem.project_name == project_name)
    result = await db.execute(q)
    items = result.scalars().all()

    query_emb = embed_text(query)
    scored: List[tuple[MemoryItem, float]] = []

    # Try FAISS first for embedding-based search
    faiss_hits: dict[str, float] = {}
    if query_emb:
        for item_id, score in search_faiss(query_emb, limit * 2):
            faiss_hits[item_id] = score

    for item in items:
        if item.id in faiss_hits:
            score = faiss_hits[item.id]
        else:
            score = hybrid_score(query, item.content, query_emb, item.embedding)
        scored.append((item, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:limit]
    for item, score in top:
        item.relevance_score = score

    return [item for item, _ in top]


async def store_review_findings(
    db: AsyncSession,
    review_json: str,
    project_name: Optional[str] = None,
):
    """Extract risks, requirements, decisions from review and save as MemoryItems."""
    try:
        data = json.loads(review_json)
    except (json.JSONDecodeError, TypeError):
        return

    # Risks
    for risk in data.get("risks", []):
        desc = risk.get("description", "")
        if desc:
            await store_memory(db, "risk", desc, ["review", risk.get("severity", "medium")], project_name)

    # Missing requirements
    for req in data.get("missing_requirements", []):
        if req:
            await store_memory(db, "requirement", req, ["review", "missing"], project_name)

    # Architecture risks
    for arch_risk in data.get("architecture_risks", []):
        if arch_risk:
            await store_memory(db, "risk", arch_risk, ["review", "architecture"], project_name)

    # Related decisions
    for dec in data.get("related_decisions", []):
        if dec:
            await store_memory(db, "decision", dec, ["review", "related"], project_name)

    # Lessons learned
    for lesson in data.get("lessons_learned", []):
        if lesson:
            await store_memory(db, "episodic", lesson, ["review", "lesson"], project_name)


async def get_recent_memory(
    db: AsyncSession,
    memory_type: Optional[str] = None,
    limit: int = 20,
) -> List[MemoryItem]:
    q = select(MemoryItem).order_by(desc(MemoryItem.created_at))
    if memory_type:
        q = q.where(MemoryItem.memory_type == memory_type)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def get_memory_context(
    db: AsyncSession,
    project_name: Optional[str] = None,
) -> dict:
    """Return memory context summary for LLM prompts."""
    risks_q = select(MemoryItem).where(MemoryItem.memory_type == "risk").limit(5)
    lessons_q = select(MemoryItem).where(MemoryItem.memory_type == "episodic").limit(5)
    decisions_q = select(MemoryItem).where(MemoryItem.memory_type == "decision").limit(5)

    if project_name:
        risks_q = risks_q.where(MemoryItem.project_name == project_name)
        lessons_q = lessons_q.where(MemoryItem.project_name == project_name)
        decisions_q = decisions_q.where(MemoryItem.project_name == project_name)

    risks = (await db.execute(risks_q)).scalars().all()
    lessons = (await db.execute(lessons_q)).scalars().all()
    decisions = (await db.execute(decisions_q)).scalars().all()

    return {
        "memory_risks": "; ".join(r.content[:200] for r in risks),
        "memory_lessons": "; ".join(l.content[:200] for l in lessons),
        "memory_decisions": "; ".join(d.content[:200] for d in decisions),
    }


async def rebuild_faiss_index(db: AsyncSession):
    """Rebuild the FAISS index from all existing memory items."""
    from app.services.embeddings import build_faiss_index

    result = await db.execute(select(MemoryItem).where(MemoryItem.embedding.isnot(None)))
    items = result.scalars().all()
    embeddings = [(item.id, item.embedding) for item in items if item.embedding]
    build_faiss_index(embeddings)
