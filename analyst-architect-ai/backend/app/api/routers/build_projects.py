"""
Build Projects router — экономический модуль.

Позволяет:
  - создать "проект-приложение", которое строится через AnalystGuru
  - запустить AI-декомпозицию задач
  - рассчитать экономику (CAPEX/OPEX/ROI/payback) по прозрачным формулам
  - внести фактические данные после внедрения (план/факт)
  - получить сводный отчёт и экспортировать бизнес-кейс в DOCX
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.document import Document
from app.models.build_project import BuildProject
from app.models.task_estimate import TaskEstimate
from app.models.economic_estimate import EconomicEstimate
from app.models.economic_actual import EconomicActual
from app.schemas import (
    BuildProjectCreate, BuildProjectOut, TaskEstimateOut,
    EconomicEstimateIn, EconomicEstimateOut, EconomicActualIn, EconomicActualOut,
    BuildProjectReportOut,
)
from app.services import task_estimator, economics_service, export_service
from app.services.audit_service import with_audit

router = APIRouter(prefix="/build-projects", tags=["economics"])


@router.post("", response_model=BuildProjectOut)
async def create_build_project(body: BuildProjectCreate, db: AsyncSession = Depends(get_db)):
    doc_res = await db.execute(select(Document).where(Document.id == body.document_id))
    if not doc_res.scalar_one_or_none():
        raise HTTPException(404, "Source document not found")

    project = BuildProject(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        document_id=body.document_id,
        name=body.name,
        description=body.description,
        status="draft",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=List[BuildProjectOut])
async def list_build_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BuildProject).order_by(desc(BuildProject.created_at)))
    return result.scalars().all()


@router.get("/{project_id}", response_model=BuildProjectOut)
async def get_build_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BuildProject).where(BuildProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Build project not found")
    return project


@router.post("/{project_id}/estimate-tasks", response_model=TaskEstimateOut)
async def estimate_project_tasks(project_id: str, db: AsyncSession = Depends(get_db)):
    """AI-декомпозиция требований проекта на задачи с оценкой часов по ролям."""
    proj_res = await db.execute(select(BuildProject).where(BuildProject.id == project_id))
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Build project not found")

    doc_res = await db.execute(select(Document).where(Document.id == project.document_id))
    document = doc_res.scalar_one_or_none()
    if not document:
        raise HTTPException(404, "Source document not found")

    async def _run():
        return await task_estimator.estimate_tasks(document.text, project.name)

    schema = await with_audit(db, "estimate_tasks", {"project_id": project_id}, _run)

    total_hours = sum(schema.total_hours_by_role.values()) if schema.total_hours_by_role else 0.0

    estimate = TaskEstimate(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        project_id=project_id,
        tasks_json=json.dumps(schema.model_dump(), ensure_ascii=False),
        total_hours=total_hours,
        confidence=schema.confidence,
        needs_review=schema.needs_review,
    )
    db.add(estimate)

    if project.status == "draft":
        project.status = "estimated"

    await db.commit()
    await db.refresh(estimate)
    return estimate


@router.post("/{project_id}/economic-estimate", response_model=EconomicEstimateOut)
async def create_economic_estimate(
    project_id: str,
    body: EconomicEstimateIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Рассчитать CAPEX/OPEX/Benefit/Payback/ROI по прозрачным формулам.
    Использует часы из последней AI-декомпозиции задач, либо manual_hours_by_role
    из тела запроса, если декомпозиция ещё не запускалась.
    """
    proj_res = await db.execute(select(BuildProject).where(BuildProject.id == project_id))
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Build project not found")

    hours_by_role = body.manual_hours_by_role
    if not hours_by_role:
        te_res = await db.execute(
            select(TaskEstimate)
            .where(TaskEstimate.project_id == project_id)
            .order_by(desc(TaskEstimate.created_at))
            .limit(1)
        )
        latest = te_res.scalar_one_or_none()
        if latest:
            hours_by_role = json.loads(latest.tasks_json).get("total_hours_by_role", {})
        else:
            raise HTTPException(
                400,
                "No task estimate found. Run POST /estimate-tasks first, "
                "or provide manual_hours_by_role.",
            )

    calc = economics_service.full_economic_calculation(hours_by_role, body)

    estimate = EconomicEstimate(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        project_id=project_id,
        rate_backend=body.rate_backend,
        rate_frontend=body.rate_frontend,
        rate_qa=body.rate_qa,
        rate_devops=body.rate_devops,
        rate_analyst=body.rate_analyst,
        hosting_cost_monthly=body.hosting_cost_monthly,
        llm_cost_monthly=body.llm_cost_monthly,
        support_hours_monthly=body.support_hours_monthly,
        time_saved_hours_monthly=body.time_saved_hours_monthly,
        avg_employee_rate=body.avg_employee_rate,
        **calc,
    )
    db.add(estimate)

    if project.status in ("draft", "estimated"):
        project.status = "approved"

    await db.commit()
    await db.refresh(estimate)
    return estimate


@router.post("/{project_id}/actuals", response_model=EconomicActualOut)
async def add_economic_actual(
    project_id: str,
    body: EconomicActualIn,
    db: AsyncSession = Depends(get_db),
):
    """Внести фактические данные после внедрения проекта (для план/факт анализа)."""
    proj_res = await db.execute(select(BuildProject).where(BuildProject.id == project_id))
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Build project not found")

    actual = EconomicActual(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        project_id=project_id,
        **body.model_dump(),
    )
    db.add(actual)
    project.status = "delivered"
    await db.commit()
    await db.refresh(actual)
    return actual


@router.get("/{project_id}/report", response_model=BuildProjectReportOut)
async def get_project_report(project_id: str, db: AsyncSession = Depends(get_db)):
    """Свод: последняя оценка задач + экономика + факт + отклонение план/факт."""
    proj_res = await db.execute(select(BuildProject).where(BuildProject.id == project_id))
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Build project not found")

    te_res = await db.execute(
        select(TaskEstimate).where(TaskEstimate.project_id == project_id)
        .order_by(desc(TaskEstimate.created_at)).limit(1)
    )
    latest_task = te_res.scalar_one_or_none()

    ee_res = await db.execute(
        select(EconomicEstimate).where(EconomicEstimate.project_id == project_id)
        .order_by(desc(EconomicEstimate.created_at)).limit(1)
    )
    latest_economic = ee_res.scalar_one_or_none()

    ea_res = await db.execute(
        select(EconomicActual).where(EconomicActual.project_id == project_id)
        .order_by(desc(EconomicActual.created_at)).limit(1)
    )
    latest_actual = ea_res.scalar_one_or_none()

    variance = {}
    if latest_economic and latest_actual:
        variance = economics_service.compute_variance(
            {
                "capex": latest_economic.capex,
                "opex_monthly": latest_economic.opex_monthly,
                "benefit_monthly": latest_economic.benefit_monthly,
            },
            {
                "actual_capex": latest_actual.actual_capex,
                "actual_opex_monthly": latest_actual.actual_opex_monthly,
                "actual_benefit_monthly": latest_actual.actual_benefit_monthly,
            },
        )

    return BuildProjectReportOut(
        project=project,
        latest_task_estimate=latest_task,
        latest_economic_estimate=latest_economic,
        latest_actual=latest_actual,
        variance=variance,
    )


@router.get("/{project_id}/export/docx")
async def export_business_case(project_id: str, db: AsyncSession = Depends(get_db)):
    """Экспорт бизнес-кейса (экономическое обоснование) в DOCX."""
    report = await get_project_report(project_id, db)

    content = {
        "summary": f"Бизнес-кейс проекта «{report.project.name}» — статус: {report.project.status}",
        "risks": [],
        "questions_to_client": [],
        "acceptance_criteria": [],
    }
    if report.latest_economic_estimate:
        e = report.latest_economic_estimate
        content["acceptance_criteria"] = [
            f"CAPEX: {e.capex:,.0f} руб.",
            f"OPEX/мес: {e.opex_monthly:,.0f} руб.",
            f"Выгода/мес: {e.benefit_monthly:,.0f} руб.",
            f"Срок окупаемости: {e.payback_months if e.payback_months > 0 else 'не окупается'} мес.",
            f"ROI за 12 мес.: {e.roi_12m_pct}%",
        ]

    docx_bytes = export_service.export_document_docx(
        f"Бизнес-кейс: {report.project.name}", content
    )
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=business_case_{project_id[:8]}.docx"},
    )


@router.get("/{project_id}/export/pdf")
async def export_business_case_pdf(project_id: str, db: AsyncSession = Depends(get_db)):
    """Экспорт бизнес-кейса в PDF."""
    report = await get_project_report(project_id, db)
    pdf_bytes = export_service.export_business_case_pdf(
        f"Бизнес-кейс: {report.project.name}", report
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=business_case_{project_id[:8]}.pdf"},
    )
