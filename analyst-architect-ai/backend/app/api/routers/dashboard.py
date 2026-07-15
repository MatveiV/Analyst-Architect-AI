"""
Dashboard router — сводная панель для менеджера/тимлида.
Объединяет статистику аудита, документов, рецензий и экономики build-проектов.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models.document import Document
from app.models.review import Review
from app.models.audit_run import AuditRun
from app.models.build_project import BuildProject
from app.models.economic_estimate import EconomicEstimate

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    total_docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    total_reviews = (await db.execute(select(func.count(Review.id)))).scalar() or 0
    needs_review_count = (await db.execute(
        select(func.count(Review.id)).where(Review.needs_review == True)  # noqa: E712
    )).scalar() or 0

    total_audit = (await db.execute(select(func.count(AuditRun.id)))).scalar() or 0
    avg_duration = (await db.execute(select(func.avg(AuditRun.duration_ms)))).scalar() or 0

    total_projects = (await db.execute(select(func.count(BuildProject.id)))).scalar() or 0

    avg_roi = (await db.execute(select(func.avg(EconomicEstimate.roi_12m_pct)))).scalar() or 0
    avg_payback = (await db.execute(
        select(func.avg(EconomicEstimate.payback_months)).where(EconomicEstimate.payback_months > 0)
    )).scalar() or 0

    return {
        "documents": {
            "total": total_docs,
        },
        "reviews": {
            "total": total_reviews,
            "needs_review": needs_review_count,
            "needs_review_pct": round((needs_review_count / total_reviews * 100), 1) if total_reviews else 0,
        },
        "audit": {
            "total_operations": total_audit,
            "avg_duration_ms": round(avg_duration, 1),
        },
        "economics": {
            "total_build_projects": total_projects,
            "avg_roi_12m_pct": round(avg_roi, 1),
            "avg_payback_months": round(avg_payback, 1),
        },
    }


@router.get("/recent-activity")
async def recent_activity(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditRun).order_by(desc(AuditRun.created_at)).limit(limit)
    )
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "created_at": r.created_at,
            "action": r.action,
            "status": r.status,
            "duration_ms": r.duration_ms,
        }
        for r in runs
    ]
