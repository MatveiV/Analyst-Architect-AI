"""
Project Lessons — управление уроками проектов.
"""
import csv
import io
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.project_lesson import ProjectLesson
from app.schemas import ProjectLessonIn, ProjectLessonOut

router = APIRouter(prefix="/lessons", tags=["lessons"])


def _row_to_out(row: ProjectLesson) -> ProjectLessonOut:
    return ProjectLessonOut(
        id=row.id,
        created_at=row.created_at or datetime.utcnow(),
        updated_at=row.updated_at or datetime.utcnow(),
        project_name=row.project_name,
        title=row.title,
        description=row.description or "",
        category=row.category,
        impact_type=row.impact_type,
        root_cause=row.root_cause,
        recommendation=row.recommendation,
        document_id=row.document_id,
        source=row.source,
    )


@router.get("", response_model=List[ProjectLessonOut])
async def list_lessons(
    project_name: Optional[str] = None,
    category: Optional[str] = None,
    impact_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(ProjectLesson).order_by(desc(ProjectLesson.created_at))
    if project_name:
        q = q.where(ProjectLesson.project_name == project_name)
    if category:
        q = q.where(ProjectLesson.category == category)
    if impact_type:
        q = q.where(ProjectLesson.impact_type == impact_type)
    result = await db.execute(q)
    return [_row_to_out(r) for r in result.scalars().all()]


# Static routes before parameterized /{lesson_id}
@router.get("/export/csv")
async def export_lessons_csv(
    project_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(ProjectLesson).order_by(desc(ProjectLesson.created_at))
    if project_name:
        q = q.where(ProjectLesson.project_name == project_name)
    result = await db.execute(q)
    rows = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Category", "Impact", "Root Cause", "Recommendation", "Project", "Source"])
    for r in rows:
        writer.writerow([
            r.title, r.category, r.impact_type,
            r.root_cause or "", r.recommendation or "",
            r.project_name, r.source,
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=project_lessons.csv"},
    )


@router.get("/{lesson_id}", response_model=ProjectLessonOut)
async def get_lesson(lesson_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProjectLesson).where(ProjectLesson.id == lesson_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Lesson not found")
    return _row_to_out(row)


@router.post("", response_model=ProjectLessonOut)
async def create_lesson(body: ProjectLessonIn, db: AsyncSession = Depends(get_db)):
    row = ProjectLesson(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        project_name=body.project_name,
        title=body.title,
        description=body.description,
        category=body.category,
        impact_type=body.impact_type,
        root_cause=body.root_cause,
        recommendation=body.recommendation,
        document_id=body.document_id,
        source="manual",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _row_to_out(row)


@router.put("/{lesson_id}", response_model=ProjectLessonOut)
async def update_lesson(lesson_id: str, body: ProjectLessonIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProjectLesson).where(ProjectLesson.id == lesson_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Lesson not found")

    row.title = body.title
    row.description = body.description
    row.category = body.category
    row.impact_type = body.impact_type
    row.root_cause = body.root_cause
    row.recommendation = body.recommendation
    row.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(row)
    return _row_to_out(row)


@router.delete("/{lesson_id}")
async def delete_lesson(lesson_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProjectLesson).where(ProjectLesson.id == lesson_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Lesson not found")
    await db.delete(row)
    await db.commit()
    return {"deleted": lesson_id}
