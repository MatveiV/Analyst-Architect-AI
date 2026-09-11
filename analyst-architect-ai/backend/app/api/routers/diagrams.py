import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.database import get_db
from app.models.diagram_artifact import DiagramArtifact
from app.models.diagram_version import DiagramVersion
from app.models.document import Document
from app.schemas import DiagramArtifactOut, DiagramUpdateIn, DiagramVersionOut
from app.services import diagram_engine
from app.services.audit_service import with_audit

router = APIRouter(prefix="/diagrams", tags=["diagrams"])


@router.get("/{diagram_id}", response_model=DiagramArtifactOut)
async def get_diagram(diagram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DiagramArtifact).where(DiagramArtifact.id == diagram_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(404, "Diagram not found")
    return artifact


@router.get("/document/{doc_id}", response_model=List[DiagramArtifactOut])
async def get_document_diagrams(
    doc_id: str,
    notation: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(DiagramArtifact).where(DiagramArtifact.document_id == doc_id)
    if notation:
        q = q.where(DiagramArtifact.notation == notation)
    result = await db.execute(q)
    return result.scalars().all()


async def _get_artifact_or_404(db: AsyncSession, diagram_id: str) -> DiagramArtifact:
    result = await db.execute(select(DiagramArtifact).where(DiagramArtifact.id == diagram_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(404, "Diagram not found")
    return artifact


async def _next_version_number(db: AsyncSession, diagram_id: str) -> int:
    result = await db.execute(
        select(func.max(DiagramVersion.version_number)).where(
            DiagramVersion.diagram_artifact_id == diagram_id
        )
    )
    current_max = result.scalar()
    return (current_max or 0) + 1


@router.put("/{diagram_id}", response_model=DiagramArtifactOut)
async def update_diagram(
    diagram_id: str,
    body: DiagramUpdateIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Эпик A3: правка исходного кода диаграммы. Предыдущая версия сохраняется в
    diagram_versions ПЕРЕД перезаписью — история не теряется. Диаграмма перерендеривается
    локально сразу же (Эпик A1/A2).
    """
    artifact = await _get_artifact_or_404(db, diagram_id)

    next_version = await _next_version_number(db, diagram_id)
    db.add(DiagramVersion(
        id=str(uuid.uuid4()),
        diagram_artifact_id=diagram_id,
        version_number=next_version,
        source_code=artifact.source_code,
        notation=artifact.notation,
        created_at=datetime.utcnow(),
        change_note=body.change_note or None,
    ))

    artifact.source_code = body.source_code
    render = await diagram_engine.render_diagram(body.source_code, artifact.notation)
    artifact.render_svg = render["render_svg"]
    artifact.render_png = render["render_png"]
    artifact.render_status = render["render_status"]
    artifact.render_error = render["render_error"]
    artifact.rendered_at = datetime.utcnow() if render["render_status"] == "ok" else None

    await db.commit()
    await db.refresh(artifact)
    return artifact


@router.get("/{diagram_id}/versions", response_model=List[DiagramVersionOut])
async def get_diagram_versions(diagram_id: str, db: AsyncSession = Depends(get_db)):
    await _get_artifact_or_404(db, diagram_id)
    result = await db.execute(
        select(DiagramVersion)
        .where(DiagramVersion.diagram_artifact_id == diagram_id)
        .order_by(desc(DiagramVersion.version_number))
    )
    return result.scalars().all()


@router.post("/{diagram_id}/rollback/{version_number}", response_model=DiagramArtifactOut)
async def rollback_diagram(
    diagram_id: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
):
    """Откат к указанной версии. Сам откат тоже создаёт новую запись версии — история
    не перезаписывается и не теряется (rollback ≠ удаление истории)."""
    artifact = await _get_artifact_or_404(db, diagram_id)
    result = await db.execute(
        select(DiagramVersion).where(
            DiagramVersion.diagram_artifact_id == diagram_id,
            DiagramVersion.version_number == version_number,
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, f"Version {version_number} not found for this diagram")

    next_version = await _next_version_number(db, diagram_id)
    db.add(DiagramVersion(
        id=str(uuid.uuid4()),
        diagram_artifact_id=diagram_id,
        version_number=next_version,
        source_code=artifact.source_code,
        notation=artifact.notation,
        created_at=datetime.utcnow(),
        change_note=f"auto-saved before rollback to v{version_number}",
    ))

    artifact.source_code = target.source_code
    render = await diagram_engine.render_diagram(target.source_code, artifact.notation)
    artifact.render_svg = render["render_svg"]
    artifact.render_png = render["render_png"]
    artifact.render_status = render["render_status"]
    artifact.render_error = render["render_error"]
    artifact.rendered_at = datetime.utcnow() if render["render_status"] == "ok" else None

    await db.commit()
    await db.refresh(artifact)
    return artifact


@router.post("/generate-c4")
async def generate_c4(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    async def _run():
        data = await diagram_engine.generate_c4_diagrams(doc.text, doc.title)
        class R:
            needs_review = False
            def model_dump(self): return data
        return R()

    r = await with_audit(db, "generate_c4", {"document_id": doc_id}, _run)
    return r.model_dump()


@router.post("/generate-uml")
async def generate_uml(doc_id: str, standard: str = "UML_ISO_19505", db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    async def _run():
        data = await diagram_engine.generate_uml_diagrams(doc.text)
        class R:
            needs_review = False
            def model_dump(self): return data
        return R()

    r = await with_audit(db, "generate_uml", {"document_id": doc_id, "standard": standard}, _run)
    return r.model_dump()


@router.post("/generate-erd")
async def generate_erd(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    async def _run():
        code = await diagram_engine.generate_erd(doc.text)
        class R:
            needs_review = False
            def model_dump(self): return {"erd": code}
        return R()

    r = await with_audit(db, "generate_erd", {"document_id": doc_id}, _run)
    return r.model_dump()
