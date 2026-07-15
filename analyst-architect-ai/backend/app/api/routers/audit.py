from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.audit_run import AuditRun
from app.schemas import AuditRunOut
from app.services.audit_service import get_audit_runs

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=List[AuditRunOut])
async def list_audit_runs(
    action: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await get_audit_runs(db, action=action, status=status, limit=limit, offset=offset)


@router.get("/stats")
async def audit_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(AuditRun.id)))).scalar()
    errors = (await db.execute(
        select(func.count(AuditRun.id)).where(AuditRun.status == "error")
    )).scalar()
    needs_review = (await db.execute(
        select(func.count(AuditRun.id)).where(AuditRun.status == "needs_review")
    )).scalar()
    avg_duration = (await db.execute(
        select(func.avg(AuditRun.duration_ms))
    )).scalar()

    return {
        "total": total,
        "ok": total - errors - needs_review,
        "errors": errors,
        "needs_review": needs_review,
        "avg_duration_ms": round(avg_duration or 0, 1),
        "error_rate_pct": round((errors / total * 100) if total else 0, 1),
        "needs_review_pct": round((needs_review / total * 100) if total else 0, 1),
    }
