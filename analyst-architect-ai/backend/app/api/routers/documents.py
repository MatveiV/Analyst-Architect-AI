import json
import re
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.document import Document
from app.models.review import Review
from app.models.architecture_review import ArchitectureReview
from app.models.adr_record import ADRRecord
from app.models.api_spec import APISpec
from app.models.diagram_artifact import DiagramArtifact
from app.models.requirements_document import RequirementsDocument
from app.schemas import (
    DocumentCreate, DocumentOut, ReviewOut, ArchitectureReviewOut,
    ADRRecordOut, APISpecOut, DiagramArtifactOut,
    RequirementsDocumentOut, DocumentStandardsIn,
    CoverageOut, CoverageRequirementItem,
)
from app.services import ai_reviewer, rag_engine, architecture_engine
from app.services import adr_generator, doc_generator, diagram_engine, export_service
from app.services.audit_service import with_audit
from app.services.memory_service import get_memory_context, store_review_findings, rebuild_faiss_index
from app.services.review_to_catalog import store_risks_from_review, store_lessons_from_review
router = APIRouter(prefix="/documents", tags=["documents"])
# Эпик B5: плоский путь для получения одного сохранённого URS/SRS вне вложенности /documents/{id}/...
requirements_documents_router = APIRouter(tags=["documents"])


@requirements_documents_router.get("/requirements-documents/{req_doc_id}", response_model=RequirementsDocumentOut)
async def get_requirements_document(req_doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RequirementsDocument).where(RequirementsDocument.id == req_doc_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Requirements document not found")
    return row


@requirements_documents_router.get("/documents/{doc_id}/coverage", response_model=CoverageOut)
async def get_document_coverage(doc_id: str, db: AsyncSession = Depends(get_db)):
    """
    Фаза 2, упрощённая «матрица трассируемости»: агрегированные счётчики покрытия
    документа требованиями/диаграммами/критериями приёмки. Это НЕ точная привязка
    "требование → элемент диаграммы" (см. оговорку в CoverageOut) — быстрый обзор,
    где явно не хватает диаграмм, критериев приёмки или самих требований.
    """
    doc_result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Последний URS, а если его нет — последний SRS
    req_result = await db.execute(
        select(RequirementsDocument)
        .where(RequirementsDocument.document_id == doc_id)
        .order_by(desc(RequirementsDocument.created_at))
    )
    req_docs = req_result.scalars().all()
    latest_urs = next((r for r in req_docs if r.doc_kind == "urs"), None)
    latest_srs = next((r for r in req_docs if r.doc_kind == "srs"), None)
    chosen = latest_urs or latest_srs

    requirements: list[CoverageRequirementItem] = []
    requirements_source = None
    if chosen:
        content = json.loads(chosen.content_json)
        requirements_source = chosen.doc_kind
        raw_reqs = content.get("user_requirements") or content.get("functional_requirements") or []
        for r in raw_reqs:
            if isinstance(r, dict):
                requirements.append(CoverageRequirementItem(
                    id=r.get("id", ""), description=r.get("description", ""),
                ))

    diag_result = await db.execute(select(DiagramArtifact).where(DiagramArtifact.document_id == doc_id))
    diagrams = diag_result.scalars().all()
    rendered_count = sum(1 for d in diagrams if d.render_status == "ok")

    rev_result = await db.execute(
        select(Review).where(Review.document_id == doc_id).order_by(desc(Review.created_at)).limit(1)
    )
    review = rev_result.scalar_one_or_none()
    acceptance_criteria: list[str] = []
    risks_count = 0
    risks_high_count = 0
    if review:
        rc = json.loads(review.review_json)
        acceptance_criteria = rc.get("acceptance_criteria", [])
        risks = rc.get("risks", [])
        risks_count = len(risks)
        risks_high_count = sum(1 for r in risks if isinstance(r, dict) and r.get("severity") == "high")

    has_requirements = len(requirements) > 0
    has_diagrams = len(diagrams) > 0
    has_acceptance_criteria = len(acceptance_criteria) > 0

    return CoverageOut(
        document_id=doc_id,
        requirements_standard=doc.default_requirements_standard,
        diagram_standard=doc.default_diagram_standard,
        requirements=requirements,
        requirements_source=requirements_source,
        diagrams_count=len(diagrams),
        diagrams_rendered_count=rendered_count,
        diagrams_by_type=[d.diagram_type for d in diagrams],
        acceptance_criteria=acceptance_criteria,
        risks_count=risks_count,
        risks_high_count=risks_high_count,
        has_requirements=has_requirements,
        has_diagrams=has_diagrams,
        has_acceptance_criteria=has_acceptance_criteria,
        is_fully_covered=has_requirements and has_diagrams and has_acceptance_criteria,
    )

# ── helpers ───────────────────────────────────────────────────────────────────

async def _build_project_context(db, project_name: Optional[str]) -> str:
    """Build project context string from memory for injection into generator prompts."""
    if not project_name:
        return ""
    ctx = await get_memory_context(db, project_name)
    parts = []
    if ctx["memory_risks"]:
        parts.append(f"Известные риски проекта '{project_name}': {ctx['memory_risks']}")
    if ctx["memory_lessons"]:
        parts.append(f"Уроки проектов: {ctx['memory_lessons']}")
    if ctx["memory_decisions"]:
        parts.append(f"Архитектурные решения: {ctx['memory_decisions']}")
    if parts:
        return "\n\nКОНТЕКСТ ПРОЕКТА:\n" + "\n".join(parts)
    return ""

def _extract_diagrams_from_md(text: str):
    """Extract mermaid and plantuml blocks from markdown text.
    Returns list of (notation, diagram_type, code) tuples."""
    diagrams = []
    # Mermaid: ```mermaid ... ```
    for match in re.finditer(r'```mermaid\n(.*?)```', text, re.DOTALL):
        code = match.group(1).strip()
        if code:
            diagrams.append(("mermaid", "flowchart", code))
    # PlantUML: ```plantuml ... ``` or @startuml ... @enduml
    for match in re.finditer(r'```plantuml\n(.*?)```', text, re.DOTALL):
        code = match.group(1).strip()
        if code:
            diagrams.append(("plantuml", "uml", code))
    for match in re.finditer(r'@startuml(.*?)@enduml', text, re.DOTALL):
        code = ("@startuml" + match.group(1) + "@enduml").strip()
        if code and not any(d[2] == code for d in diagrams):
            diagrams.append(("plantuml", "uml", code))
    return diagrams


@router.post("", response_model=DocumentOut)
async def create_document(body: DocumentCreate, db: AsyncSession = Depends(get_db)):
    doc = Document(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        title=body.title,
        text=body.text,
        doc_type=body.doc_type,
        project_name=body.project_name or None,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Auto-index for RAG if doc_type is kb_article
    if body.doc_type == "kb_article":
        await rag_engine.index_document(db, doc.id, body.text)

    # Extract diagrams if markdown
    if body.doc_type == "markdown":
        diags = _extract_diagrams_from_md(body.text)
        for notation, dtype, code in diags:
            artifact = DiagramArtifact(
                id=str(uuid.uuid4()),
                created_at=datetime.utcnow(),
                document_id=doc.id,
                diagram_type=dtype,
                notation=notation,
                source_code=code,
            )
            db.add(artifact)
        await db.commit()

    return doc


@router.post("/upload-markdown", response_model=DocumentOut)
async def upload_markdown(
    file: UploadFile = File(...),
    project_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a .md file — extracts mermaid/plantuml diagrams automatically."""
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1251")

    title = file.filename.replace(".md", "").replace(".markdown", "") if file.filename else "Untitled"
    doc = Document(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        title=title,
        text=text,
        doc_type="markdown",
        project_name=project_name or None,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    diags = _extract_diagrams_from_md(text)
    for notation, dtype, code in diags:
        artifact = DiagramArtifact(
            id=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            document_id=doc.id,
            diagram_type=dtype,
            notation=notation,
            source_code=code,
        )
        db.add(artifact)
    await db.commit()

    return doc


@router.get("/{doc_id}/export/markdown")
async def export_markdown(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Export a consolidated final document as markdown with embedded diagrams."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Gather all related data
    rev_result = await db.execute(
        select(Review).where(Review.document_id == doc_id).order_by(desc(Review.created_at)).limit(1)
    )
    review = rev_result.scalar_one_or_none()

    arch_result = await db.execute(
        select(ArchitectureReview).where(ArchitectureReview.document_id == doc_id).order_by(desc(ArchitectureReview.created_at)).limit(1)
    )
    arch = arch_result.scalar_one_or_none()

    adr_result = await db.execute(
        select(ADRRecord).where(ADRRecord.document_id == doc_id).order_by(desc(ADRRecord.created_at)).limit(1)
    )
    adr = adr_result.scalar_one_or_none()

    diag_result = await db.execute(
        select(DiagramArtifact).where(DiagramArtifact.document_id == doc_id)
    )
    diagrams = diag_result.scalars().all()

    lines = [
        f"# {doc.title}",
        "",
        f"> **Type**: {doc.doc_type}  |  **Project**: {doc.project_name or '—'}  |  **Created**: {doc.created_at.isoformat()}",
        "",
        "---",
        "",
    ]

    if doc.doc_type != "markdown":
        lines += ["## Source Text", "", doc.text, ""]
    else:
        lines += [doc.text, ""]

    if review:
        review_data = json.loads(review.review_json)
        lines += ["---", "", "## Review", "", f"- **Confidence**: {review_data.get('confidence', '—')}", f"- **Needs Review**: {'Yes' if review_data.get('needs_review') else 'No'}", ""]
        if review_data.get("summary"):
            lines += ["### Summary", "", review_data["summary"], ""]
        if review_data.get("risks"):
            lines += ["### Risks", ""]
            for r in review_data["risks"]:
                lines += [f"- **[{r.get('severity','').upper()}]** {r.get('description', '')}"]
            lines.append("")

    if adr:
        adr_data = json.loads(adr.adr_json)
        lines += ["---", "", "## Architectural Decision Record (ADR)", "", f"**{adr_data.get('title', '')}**", "", f"**Status**: {adr_data.get('status', 'proposed')}", "", "### Context", "", adr_data.get('context', ''), "", "### Problem", "", adr_data.get('problem', ''), "", "### Decision", "", adr_data.get('decision', ''), ""]

    if diagrams:
        lines += ["---", "", "## Diagrams", ""]
        for d in diagrams:
            lang = "mermaid" if d.notation == "mermaid" else "plantuml"
            lines += [f"### {d.diagram_type} ({d.notation})", "", f"```{lang}", d.source_code, "```", ""]

    md = "\n".join(lines)
    return Response(
        content=md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={doc.title[:30]}_final.md"},
    )


@router.get("", response_model=List[DocumentOut])
async def list_documents(
    doc_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Document).order_by(desc(Document.created_at))
    if doc_type:
        q = q.where(Document.doc_type == doc_type)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("/{doc_id}/review", response_model=ReviewOut)
async def review_document(
    doc_id: str,
    reasoning_mode: str = "direct",
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    mem_ctx = await get_memory_context(db, doc.project_name)

    async def _run():
        return await ai_reviewer.run_ai_review(
            doc.text,
            memory_risks=mem_ctx["memory_risks"],
            memory_lessons=mem_ctx["memory_lessons"],
            memory_decisions=mem_ctx["memory_decisions"],
            reasoning_mode=reasoning_mode,
        )

    schema = await with_audit(
        db, "review", {"document_id": doc_id, "title": doc.title, "reasoning_mode": reasoning_mode}, _run
    )

    review_json_str = json.dumps(schema.model_dump(), ensure_ascii=False)
    review = Review(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        document_id=doc_id,
        review_json=review_json_str,
        needs_review=schema.needs_review,
        confidence=schema.confidence,
        error=None,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    # Auto-store review findings as project memory
    await store_review_findings(db, review_json_str, doc.project_name)
    await rebuild_faiss_index(db)

    # Auto-populate risk catalog and lessons-learned from review
    await store_risks_from_review(db, review_json_str, doc_id, doc.project_name)
    await store_lessons_from_review(db, review_json_str, doc_id, doc.project_name)

    return review


@router.post("/{doc_id}/generate-urs")
async def generate_urs(
    doc_id: str,
    project_name: Optional[str] = None,
    standard: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    standard_profile = standard or doc.default_requirements_standard or "ISO_IEC_IEEE_29148"
    ctx = await _build_project_context(db, project_name or doc.project_name)

    async def _run():
        return await doc_generator.generate_urs(doc.text, doc.title, ctx, standard=standard_profile)

    schema = await with_audit(
        db, "generate_urs",
        {"document_id": doc_id, "project_name": project_name, "standard": standard_profile}, _run,
    )

    # Эпик B2: персистентность URS — раньше была видна только через audit_runs.output
    req_doc = RequirementsDocument(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        doc_kind="urs",
        standard_profile=standard_profile,
        content_json=json.dumps(schema.model_dump(), ensure_ascii=False),
        confidence=schema.confidence,
        needs_review=schema.needs_review,
        created_at=datetime.utcnow(),
    )
    db.add(req_doc)
    await db.commit()

    return schema.model_dump()


@router.post("/{doc_id}/generate-srs")
async def generate_srs(
    doc_id: str,
    project_name: Optional[str] = None,
    standard: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    standard_profile = standard or doc.default_requirements_standard or "ISO_IEC_IEEE_29148"
    ctx = await _build_project_context(db, project_name or doc.project_name)

    async def _run():
        return await doc_generator.generate_srs(doc.text, doc.title, ctx, standard=standard_profile)

    schema = await with_audit(
        db, "generate_srs",
        {"document_id": doc_id, "project_name": project_name, "standard": standard_profile}, _run,
    )

    req_doc = RequirementsDocument(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        doc_kind="srs",
        standard_profile=standard_profile,
        content_json=json.dumps(schema.model_dump(), ensure_ascii=False),
        confidence=schema.confidence,
        needs_review=schema.needs_review,
        created_at=datetime.utcnow(),
    )
    db.add(req_doc)
    await db.commit()

    return schema.model_dump()


@router.patch("/{doc_id}/standards", response_model=DocumentOut)
async def set_document_standards(
    doc_id: str,
    body: DocumentStandardsIn,
    db: AsyncSession = Depends(get_db),
):
    """Эпик B5: задать дефолтные стандарты требований/диаграмм для документа —
    последующие generate-urs/srs/diagrams без явного ?standard= будут их использовать."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    if body.default_requirements_standard is not None:
        doc.default_requirements_standard = body.default_requirements_standard
    if body.default_diagram_standard is not None:
        doc.default_diagram_standard = body.default_diagram_standard
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/{doc_id}/requirements-documents", response_model=List[RequirementsDocumentOut])
async def list_requirements_documents(doc_id: str, db: AsyncSession = Depends(get_db)):
    """История сгенерированных URS/SRS — можно сравнить один и тот же документ,
    сгенерированный по разным стандартам (напр. ГОСТ 34 vs ISO/IEC/IEEE 29148)."""
    result = await db.execute(
        select(RequirementsDocument)
        .where(RequirementsDocument.document_id == doc_id)
        .order_by(desc(RequirementsDocument.created_at))
    )
    return result.scalars().all()


@router.post("/{doc_id}/generate-adr", response_model=ADRRecordOut)
async def generate_adr(
    doc_id: str,
    project_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    ctx = await _build_project_context(db, project_name or doc.project_name)

    async def _run():
        return await adr_generator.generate_adr(doc.text, ctx)

    schema = await with_audit(db, "generate_adr", {"document_id": doc_id, "project_name": project_name}, _run)

    record = ADRRecord(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        document_id=doc_id,
        adr_json=json.dumps(schema.model_dump(), ensure_ascii=False),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.post("/{doc_id}/recommend-architecture", response_model=ArchitectureReviewOut)
async def recommend_architecture(
    doc_id: str,
    project_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    ctx = await _build_project_context(db, project_name or doc.project_name)

    async def _run():
        return await architecture_engine.recommend_architecture(doc.text, ctx)

    schema = await with_audit(db, "recommend_architecture", {"document_id": doc_id, "project_name": project_name}, _run)

    arch_review = ArchitectureReview(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        document_id=doc_id,
        recommendation_json=json.dumps(schema.model_dump(), ensure_ascii=False),
        needs_review=schema.needs_review,
    )
    db.add(arch_review)
    await db.commit()
    await db.refresh(arch_review)
    return arch_review


@router.post("/{doc_id}/design-api", response_model=APISpecOut)
async def design_api(
    doc_id: str,
    project_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    ctx = await _build_project_context(db, project_name or doc.project_name)

    async def _run_api():
        j, y = await doc_generator.generate_api_spec(doc.text, doc.title, ctx)
        # Return a simple container for audit
        class R:
            needs_review = False
            def model_dump(self): return {"json": j[:200]}
        return R()

    await with_audit(db, "design_api", {"document_id": doc_id, "project_name": project_name}, _run_api)
    j, y = await doc_generator.generate_api_spec(doc.text, doc.title, ctx)

    spec = APISpec(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        document_id=doc_id,
        openapi_json=j,
        openapi_yaml=y,
    )
    db.add(spec)
    await db.commit()
    await db.refresh(spec)
    return spec


@router.post("/{doc_id}/generate-diagrams")
async def generate_diagrams(
    doc_id: str,
    project_name: Optional[str] = None,
    standard: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Эпик B5: явный параметр > дефолт документа > дефолт системы (C4)
    standard_profile = standard or doc.default_diagram_standard or "C4_MODEL"
    ctx = await _build_project_context(db, project_name or doc.project_name)

    async def _run():
        return await diagram_engine.generate_all_diagrams(doc.text, doc.title, ctx, standard=standard_profile)

    schema = await with_audit(
        db, "generate_diagrams",
        {"document_id": doc_id, "project_name": project_name, "standard": standard_profile},
        _run,
    )

    # Store each diagram type
    diagram_map = {
        "c4_context": ("plantuml", schema.c4_context),
        "c4_container": ("plantuml", schema.c4_container),
        "c4_component": ("plantuml", schema.c4_component),
        "use_case": ("plantuml", schema.use_case),
        "sequence": ("plantuml", schema.sequence),
        "class": ("plantuml", schema.class_diagram),
        "erd": ("plantuml", schema.erd),
        "flowchart": ("mermaid", schema.mermaid_flowchart),
    }
    for i, vp in enumerate(schema.viewpoints or []):
        if vp.diagram_code:
            diagram_map[f"viewpoint_{i}_{vp.name or i}"] = ("plantuml", vp.diagram_code)

    created = []
    for dtype, (notation, code) in diagram_map.items():
        if not code:
            continue
        artifact = DiagramArtifact(
            id=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            document_id=doc_id,
            diagram_type=dtype,
            notation=notation,
            source_code=code,
            standard_profile=standard_profile,
        )
        # Эпик A2: рендерим локально сразу при генерации, а не только по запросу фронтенда
        render = await diagram_engine.render_diagram(code, notation)
        artifact.render_svg = render["render_svg"]
        artifact.render_png = render["render_png"]
        artifact.render_status = render["render_status"]
        artifact.render_error = render["render_error"]
        artifact.rendered_at = datetime.utcnow() if render["render_status"] == "ok" else None
        db.add(artifact)
        created.append({"type": dtype, "notation": notation, "render_status": render["render_status"]})

    await db.commit()
    return {"created": created, "needs_review": schema.needs_review, "standard_profile": standard_profile}


@router.get("/{doc_id}/export/docx")
async def export_docx(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Get latest review if exists
    rev_result = await db.execute(
        select(Review).where(Review.document_id == doc_id).order_by(desc(Review.created_at)).limit(1)
    )
    review = rev_result.scalar_one_or_none()
    content = json.loads(review.review_json) if review else {"text": doc.text}

    docx_bytes = export_service.export_document_docx(doc.title, content)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={doc.title[:30]}.docx"},
    )


@router.get("/{doc_id}/export/full-package/docx")
async def export_full_package_docx(doc_id: str, db: AsyncSession = Depends(get_db)):
    """
    Эпик A4: единый DOCX — рецензия + все диаграммы (картинками, не кодом) + отметка
    применённого стандарта. Диаграммы без успешного локального рендера (render_status != "ok")
    попадают в документ как код с явной пометкой "рендер недоступен".
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    rev_result = await db.execute(
        select(Review).where(Review.document_id == doc_id).order_by(desc(Review.created_at)).limit(1)
    )
    review = rev_result.scalar_one_or_none()
    content = json.loads(review.review_json) if review else {"text": doc.text}
    content["standard_profile"] = (review.standard_profile if review else None) or doc.default_requirements_standard

    diag_result = await db.execute(
        select(DiagramArtifact).where(DiagramArtifact.document_id == doc_id).order_by(DiagramArtifact.diagram_type)
    )
    diagrams = diag_result.scalars().all()

    docx_bytes = export_service.export_document_docx(doc.title, content, diagrams=diagrams)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={doc.title[:30]}_full.docx"},
    )
