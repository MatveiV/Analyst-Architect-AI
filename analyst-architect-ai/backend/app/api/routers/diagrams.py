from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.diagram_artifact import DiagramArtifact
from app.models.document import Document
from app.schemas import DiagramArtifactOut
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
async def generate_uml(doc_id: str, db: AsyncSession = Depends(get_db)):
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

    r = await with_audit(db, "generate_uml", {"document_id": doc_id}, _run)
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
