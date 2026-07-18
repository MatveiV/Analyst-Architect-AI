import json
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.document import Document
from app.models.qa_run import QARun
from app.schemas import DocumentCreate, DocumentOut, KBQuestionRequest, QARunOut, DirectAnswerRequest
from app.services import rag_engine
from app.services.audit_service import with_audit

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


@router.post("/documents", response_model=DocumentOut)
async def add_kb_document(body: DocumentCreate, db: AsyncSession = Depends(get_db)):
    doc = Document(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        title=body.title,
        text=body.text,
        doc_type="kb_article",
        project_name=body.project_name,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Index for RAG
    await rag_engine.index_document(db, doc.id, body.text)
    return doc


@router.get("/documents", response_model=List[DocumentOut])
async def list_kb_documents(db: AsyncSession = Depends(get_db)):
    q = select(Document).where(Document.doc_type == "kb_article").order_by(desc(Document.created_at))
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/ask")
async def ask_knowledge_base(body: KBQuestionRequest, db: AsyncSession = Depends(get_db)):
    async def _run():
        snippets = await rag_engine.retrieve_snippets(db, body.question)

        # Build document title map
        doc_ids = list({s.document_id for s, _ in snippets})
        doc_map = {}
        if doc_ids:
            docs_q = await db.execute(select(Document).where(Document.id.in_(doc_ids)))
            for d in docs_q.scalars().all():
                doc_map[d.id] = d.title

        return await rag_engine.answer_with_sources(body.question, snippets, doc_map)

    schema = await with_audit(db, "ask_kb", {"question": body.question}, _run)

    qa = QARun(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        question=body.question,
        answer=schema.answer,
        sources_json=json.dumps([s.model_dump() for s in schema.sources], ensure_ascii=False),
        needs_review=schema.needs_review,
        error="NO_SOURCES_FOUND" if not schema.sources else None,
    )
    db.add(qa)
    await db.commit()

    return {
        "answer": schema.answer,
        "sources": [s.model_dump() for s in schema.sources],
        "confidence": schema.confidence,
        "needs_review": schema.needs_review,
        "qa_run_id": qa.id,
    }


@router.get("/history", response_model=List[QARunOut])
async def get_qa_history(
    needs_review: Optional[bool] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    q = select(QARun).order_by(desc(QARun.created_at)).limit(limit)
    if needs_review is not None:
        q = q.where(QARun.needs_review == needs_review)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/reindex")
async def reindex_kb(db: AsyncSession = Depends(get_db)):
    """Re-index all KB documents."""
    q = select(Document).where(Document.doc_type == "kb_article")
    result = await db.execute(q)
    docs = result.scalars().all()

    indexed = 0
    for doc in docs:
        await rag_engine.index_document(db, doc.id, doc.text)
        indexed += 1

    # Эпик A5: полная пересборка FAISS после reindex — index_document делает delete+insert
    # снипетов, а инкрементальный faiss.add() не умеет удалять старые векторы, поэтому
    # после массового reindex собираем индекс с нуля, а не полагаемся на инкремент.
    faiss_count = await rag_engine.rebuild_snippet_faiss_index(db)

    return {"indexed": indexed, "faiss_indexed": faiss_count}


@router.post("/ai/answer_with_sources")
async def direct_answer(body: DirectAnswerRequest, db: AsyncSession = Depends(get_db)):
    """Direct AI call for testing."""
    async def _run():
        if body.context:
            # Create mock snippets from context
            from app.models.snippet import Snippet
            mock_snippet = Snippet(
                id="mock",
                document_id="mock",
                snippet_text=body.context,
                embedding=None,
            )
            return await rag_engine.answer_with_sources(body.question, [(mock_snippet, 1.0)])
        else:
            snippets = await rag_engine.retrieve_snippets(db, body.question)
            return await rag_engine.answer_with_sources(body.question, snippets)

    schema = await with_audit(db, "direct_answer", {"question": body.question}, _run)
    return schema.model_dump()
