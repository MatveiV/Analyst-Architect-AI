"""
Dashboard router — сводная панель для менеджера/тимлида.
Объединяет статистику аудита, документов, рецензий и экономики build-проектов.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, Integer

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


@router.get("/stats-by-provider")
async def stats_by_provider(db: AsyncSession = Depends(get_db)):
    """
    Эпик C6: честная разбивка audit_runs по фактически использованному LLM-провайдеру.
    Показывает, что локальные модели (Ollama) обычно дешевле по OPEX, но чаще требуют
    needs_review/дают ошибку формата JSON — решение "когда использовать локальную модель,
    а когда облачную" принимает аналитик на основе этих цифр, а не декларации.
    """
    result = await db.execute(
        select(
            AuditRun.provider_used,
            AuditRun.is_local_provider,
            func.count(AuditRun.id).label("total"),
            func.sum(func.cast(AuditRun.status == "error", Integer)).label("errors"),
            func.sum(func.cast(AuditRun.status == "needs_review", Integer)).label("needs_review"),
            func.avg(AuditRun.duration_ms).label("avg_duration"),
        )
        .where(AuditRun.provider_used.isnot(None))
        .group_by(AuditRun.provider_used, AuditRun.is_local_provider)
    )
    rows = result.all()
    stats = []
    for provider_used, is_local, total, errors, needs_review, avg_duration in rows:
        total = total or 0
        stats.append({
            "provider": provider_used,
            "is_local": bool(is_local),
            "total_runs": total,
            "error_rate_pct": round((errors or 0) / total * 100, 1) if total else 0,
            "needs_review_rate_pct": round((needs_review or 0) / total * 100, 1) if total else 0,
            "avg_duration_ms": round(avg_duration or 0, 1),
        })
    return sorted(stats, key=lambda s: s["total_runs"], reverse=True)
