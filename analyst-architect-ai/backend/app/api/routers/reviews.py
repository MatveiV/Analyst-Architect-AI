import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.review import Review
from app.schemas import ReviewOut, DirectReviewRequest, ReviewSchema, ReviewDiffOut
from app.services import ai_reviewer, export_service
from app.services.audit_service import with_audit
from app.services.diff_service import compute_review_diff

router = APIRouter(tags=["reviews"])


@router.get("/reviews", response_model=List[ReviewOut])
async def list_reviews(
    needs_review: Optional[bool] = None,
    document_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Review).order_by(desc(Review.created_at))
    if needs_review is not None:
        q = q.where(Review.needs_review == needs_review)
    if document_id is not None:
        q = q.where(Review.document_id == document_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/reviews/diff", response_model=ReviewDiffOut)
async def diff_reviews(from_id: str, to_id: str, db: AsyncSession = Depends(get_db)):
    """
    Фаза 2: сравнение двух рецензий — типичный сценарий: аналитик перезапускает рецензию
    после того, как заказчик прислал обновлённое ТЗ, и хочет быстро увидеть, что изменилось,
    не перечитывая обе рецензии целиком.
    """
    from_result = await db.execute(select(Review).where(Review.id == from_id))
    from_review = from_result.scalar_one_or_none()
    if not from_review:
        raise HTTPException(404, f"Review {from_id} not found")

    to_result = await db.execute(select(Review).where(Review.id == to_id))
    to_review = to_result.scalar_one_or_none()
    if not to_review:
        raise HTTPException(404, f"Review {to_id} not found")

    return compute_review_diff(from_review, to_review)


@router.get("/reviews/{review_id}", response_model=ReviewOut)
async def get_review(review_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review).where(Review.id == review_id))
    rev = result.scalar_one_or_none()
    if not rev:
        raise HTTPException(404, "Review not found")
    return rev


@router.post("/ai/review")
async def direct_ai_review(body: DirectReviewRequest, db: AsyncSession = Depends(get_db)):
    async def _run():
        return await ai_reviewer.run_ai_review(body.text, reasoning_mode=body.reasoning_mode)

    schema = await with_audit(
        db, "direct_review", {"text_len": len(body.text), "reasoning_mode": body.reasoning_mode}, _run
    )
    return schema.model_dump()


@router.get("/reviews/{review_id}/export/json")
async def export_review_json(review_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review).where(Review.id == review_id))
    rev = result.scalar_one_or_none()
    if not rev:
        raise HTTPException(404, "Review not found")

    data = json.loads(rev.review_json)
    content = export_service.export_review_json(data)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=review_{review_id[:8]}.json"},
    )


@router.get("/reviews/{review_id}/export/csv")
async def export_review_csv(review_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review).where(Review.id == review_id))
    rev = result.scalar_one_or_none()
    if not rev:
        raise HTTPException(404, "Review not found")

    data = json.loads(rev.review_json)
    content = export_service.export_review_csv(data)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename=review_{review_id[:8]}.csv"},
    )
