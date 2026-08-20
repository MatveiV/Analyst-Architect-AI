"""
Risk Catalog — управление каталогом рисков.
"""
import csv
import io
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.risk_catalog import RiskCatalogItem
from app.schemas import (
    RiskCatalogItemIn, RiskCatalogItemOut, RiskStatsOut, compute_severity,
)

router = APIRouter(prefix="/risk-catalog", tags=["risk-catalog"])


def _row_to_out(row: RiskCatalogItem) -> RiskCatalogItemOut:
    return RiskCatalogItemOut(
        id=row.id,
        created_at=row.created_at or datetime.utcnow(),
        updated_at=row.updated_at or datetime.utcnow(),
        project_name=row.project_name,
        title=row.title,
        description=row.description or "",
        probability=row.probability,
        impact=row.impact,
        severity=compute_severity(row.probability, row.impact),
        category=row.category,
        status=row.status,
        owner=row.owner,
        mitigation=row.mitigation,
        document_id=row.document_id,
        source=row.source,
    )


@router.get("", response_model=List[RiskCatalogItemOut])
async def list_risks(
    project_name: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(RiskCatalogItem).order_by(desc(RiskCatalogItem.updated_at))
    if project_name:
        q = q.where(RiskCatalogItem.project_name == project_name)
    if category:
        q = q.where(RiskCatalogItem.category == category)
    if status:
        q = q.where(RiskCatalogItem.status == status)
    result = await db.execute(q)
    rows = result.scalars().all()
    items = [_row_to_out(r) for r in rows]
    if severity:
        items = [i for i in items if i.severity == severity]
    return items


# Static routes must precede parameterized /{risk_id}
@router.get("/stats", response_model=RiskStatsOut)
async def risk_stats(
    project_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(RiskCatalogItem)
    if project_name:
        q = q.where(RiskCatalogItem.project_name == project_name)
    result = await db.execute(q)
    rows = result.scalars().all()

    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_project: dict[str, int] = {}

    for r in rows:
        sev = compute_severity(r.probability, r.impact)
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_category[r.category] = by_category.get(r.category, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
        pn = r.project_name or "(no project)"
        by_project[pn] = by_project.get(pn, 0) + 1

    return RiskStatsOut(
        total=len(rows),
        by_severity=by_severity,
        by_category=by_category,
        by_status=by_status,
        by_project=by_project,
    )


@router.get("/export/csv")
async def export_risk_csv(
    project_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(RiskCatalogItem).order_by(desc(RiskCatalogItem.updated_at))
    if project_name:
        q = q.where(RiskCatalogItem.project_name == project_name)
    result = await db.execute(q)
    rows = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Severity", "Probability", "Impact", "Category", "Status", "Owner", "Project", "Mitigation", "Source"])
    for r in rows:
        writer.writerow([
            r.title,
            compute_severity(r.probability, r.impact),
            r.probability, r.impact,
            r.category, r.status, r.owner, r.project_name,
            r.mitigation or "", r.source,
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=risk_catalog.csv"},
    )


@router.get("/{risk_id}", response_model=RiskCatalogItemOut)
async def get_risk(risk_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RiskCatalogItem).where(RiskCatalogItem.id == risk_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Risk not found")
    return _row_to_out(row)


@router.post("", response_model=RiskCatalogItemOut)
async def create_risk(body: RiskCatalogItemIn, db: AsyncSession = Depends(get_db)):
    row = RiskCatalogItem(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        project_name=body.project_name,
        title=body.title,
        description=body.description,
        probability=body.probability,
        impact=body.impact,
        category=body.category,
        status=body.status,
        owner=body.owner,
        mitigation=body.mitigation,
        document_id=body.document_id,
        source="manual",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _row_to_out(row)


@router.put("/{risk_id}", response_model=RiskCatalogItemOut)
async def update_risk(risk_id: str, body: RiskCatalogItemIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RiskCatalogItem).where(RiskCatalogItem.id == risk_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Risk not found")

    row.title = body.title
    row.description = body.description
    row.probability = body.probability
    row.impact = body.impact
    row.category = body.category
    row.status = body.status
    row.owner = body.owner
    row.mitigation = body.mitigation
    row.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(row)
    return _row_to_out(row)


@router.delete("/{risk_id}")
async def delete_risk(risk_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RiskCatalogItem).where(RiskCatalogItem.id == risk_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Risk not found")
    await db.delete(row)
    await db.commit()
    return {"deleted": risk_id}
