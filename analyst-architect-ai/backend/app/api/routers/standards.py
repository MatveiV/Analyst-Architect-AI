"""
Standards router — справочник стандартов оформления требований/документации и диаграмм.
Эпик B: пользователь выбирает стандарт (ГОСТ/ISO/IEEE/IEC/C4) для генерации URS/SRS/диаграмм.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.documentation_standard import DocumentationStandard
from app.schemas import DocumentationStandardOut

router = APIRouter(prefix="/standards", tags=["standards"])


@router.get("", response_model=List[DocumentationStandardOut])
async def list_standards(
    family: Optional[str] = None,  # "requirements" | "diagram"
    db: AsyncSession = Depends(get_db),
):
    q = select(DocumentationStandard).where(DocumentationStandard.is_active == True)  # noqa: E712
    if family:
        q = q.where(DocumentationStandard.family == family)
    q = q.order_by(DocumentationStandard.family, DocumentationStandard.id)
    result = await db.execute(q)
    return result.scalars().all()
