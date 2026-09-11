from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import MemoryStoreRequest, MemorySearchRequest, MemoryItemOut
from app.services.memory_service import store_memory, search_memory, get_recent_memory
from app.services.audit_service import save_audit

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/store", response_model=MemoryItemOut)
async def store_memory_item(body: MemoryStoreRequest, db: AsyncSession = Depends(get_db)):
    item = await store_memory(
        db,
        memory_type=body.memory_type,
        content=body.content,
        tags=body.tags,
        project_name=body.project_name,
    )
    await save_audit(db, "memory_store", body.model_dump(), {"id": item.id}, status="ok")
    return item


@router.post("/search", response_model=List[MemoryItemOut])
async def search_memory_items(body: MemorySearchRequest, db: AsyncSession = Depends(get_db)):
    items = await search_memory(
        db,
        query=body.query,
        memory_type=body.memory_type,
        project_name=body.project_name,
        limit=body.limit,
    )
    return items


@router.get("/recent", response_model=List[MemoryItemOut])
async def get_recent(
    memory_type: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await get_recent_memory(db, memory_type=memory_type, limit=limit)


@router.post("/consolidate")
async def consolidate_memory(db: AsyncSession = Depends(get_db)):
    """Simple deduplication: remove exact content duplicates."""
    from sqlalchemy import select
    from app.models.memory_item import MemoryItem

    result = await db.execute(select(MemoryItem).order_by(MemoryItem.created_at))
    items = result.scalars().all()

    seen = set()
    removed = 0
    for item in items:
        key = (item.memory_type, item.content[:200])
        if key in seen:
            await db.delete(item)
            removed += 1
        else:
            seen.add(key)

    await db.commit()
    return {"removed_duplicates": removed, "remaining": len(items) - removed}
