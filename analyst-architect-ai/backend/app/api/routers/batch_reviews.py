"""
Batch Reviews router — Фаза 2, тикет «Пакетная рецензия».
Загрузка N ТЗ одним запросом → каждое обрабатывается существующим ai_reviewer →
сводная таблица с фильтром needs_review, как и требовалось в исходном плане.
"""
import csv
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.batch_review import BatchReview
from app.models.batch_review_item import BatchReviewItem
from app.schemas import BatchReviewCreate, BatchReviewOut, BatchReviewDetailOut
from app.services.batch_review_service import create_and_process_batch

router = APIRouter(prefix="/batch-reviews", tags=["batch-reviews"])


@router.post("", response_model=BatchReviewDetailOut)
async def create_batch_review(body: BatchReviewCreate, db: AsyncSession = Depends(get_db)):
    """
    Создаёт и синхронно обрабатывает пакет ТЗ (до 50 штук за запрос). Каждый документ
    рецензируется независимо — падение одного не блокирует остальные (см. batch_review_service).
    """
    batch = await create_and_process_batch(db, body)
    result = await db.execute(
        select(BatchReviewItem)
        .where(BatchReviewItem.batch_id == batch.id)
        .order_by(BatchReviewItem.order_index)
    )
    items = result.scalars().all()
    return BatchReviewDetailOut(
        id=batch.id, created_at=batch.created_at, title=batch.title, status=batch.status,
        total_count=batch.total_count, completed_count=batch.completed_count,
        needs_review_count=batch.needs_review_count, error_count=batch.error_count,
        items=items,
    )


@router.get("", response_model=List[BatchReviewOut])
async def list_batch_reviews(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BatchReview).order_by(desc(BatchReview.created_at)))
    return result.scalars().all()


@router.get("/{batch_id}", response_model=BatchReviewDetailOut)
async def get_batch_review(
    batch_id: str,
    needs_review: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BatchReview).where(BatchReview.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch review not found")

    q = select(BatchReviewItem).where(BatchReviewItem.batch_id == batch_id)
    if needs_review is not None:
        q = q.where(BatchReviewItem.needs_review == needs_review)
    q = q.order_by(BatchReviewItem.order_index)
    items = (await db.execute(q)).scalars().all()

    return BatchReviewDetailOut(
        id=batch.id, created_at=batch.created_at, title=batch.title, status=batch.status,
        total_count=batch.total_count, completed_count=batch.completed_count,
        needs_review_count=batch.needs_review_count, error_count=batch.error_count,
        items=items,
    )


@router.get("/{batch_id}/export/csv")
async def export_batch_review_csv(batch_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BatchReview).where(BatchReview.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch review not found")

    items = (await db.execute(
        select(BatchReviewItem).where(BatchReviewItem.batch_id == batch_id).order_by(BatchReviewItem.order_index)
    )).scalars().all()

    buf = io.StringIO()
    buf.write("\ufeff")  # BOM для корректного открытия кириллицы в Excel
    writer = csv.writer(buf)
    writer.writerow(["#", "title", "status", "needs_review", "confidence", "document_id", "review_id", "error"])
    for i, it in enumerate(items, 1):
        writer.writerow([i, it.title, it.status, it.needs_review, it.confidence or "",
                          it.document_id or "", it.review_id or "", it.error or ""])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename=batch_review_{batch_id[:8]}.csv"},
    )
