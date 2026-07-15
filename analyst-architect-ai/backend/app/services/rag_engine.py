"""
RAG Engine — гибридный поиск по базе знаний.
Keyword search + косинусное сходство эмбеддингов.
"""
import json
import re
import uuid
from typing import List, Tuple
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.snippet import Snippet
from app.models.document import Document
from app.schemas import AnswerWithSourcesSchema, SourceItem
from app.services.llm_client import call_llm, extract_json
from app.services.embeddings import embed_text, cosine_sim, keyword_score


def split_into_snippets(text: str, max_len: int = 500) -> List[str]:
    """Split text by paragraphs, then by max_len."""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    result = []
    for para in paragraphs:
        if len(para) <= max_len:
            result.append(para)
        else:
            # Split long paragraphs by sentences first
            sentences = re.split(r"(?<=[.!?])\s+", para)
            chunk = ""
            for sent in sentences:
                if len(chunk) + len(sent) < max_len:
                    chunk += (" " if chunk else "") + sent
                else:
                    if chunk:
                        result.append(chunk.strip())
                    # If single sentence is still too long, hard-split by words
                    if len(sent) > max_len:
                        words = sent.split()
                        sub = ""
                        for w in words:
                            if len(sub) + len(w) + 1 < max_len:
                                sub += (" " if sub else "") + w
                            else:
                                if sub:
                                    result.append(sub.strip())
                                sub = w
                        chunk = sub
                    else:
                        chunk = sent
            if chunk:
                result.append(chunk.strip())
    return [s for s in result if len(s) > 20]


async def index_document(db: AsyncSession, document_id: str, text: str):
    """Split document into snippets, embed, and store in DB."""
    # Remove old snippets for this document
    from sqlalchemy import delete
    await db.execute(delete(Snippet).where(Snippet.document_id == document_id))

    chunks = split_into_snippets(text)
    for chunk in chunks:
        emb = embed_text(chunk)
        snippet = Snippet(
            id=str(uuid.uuid4()),
            document_id=document_id,
            snippet_text=chunk,
            embedding=emb,
        )
        db.add(snippet)
    await db.commit()





async def retrieve_snippets(
    db: AsyncSession, question: str, top_k: int | None = None
) -> List[Tuple[Snippet, float]]:
    """Hybrid retrieval: keyword + semantic similarity."""
    k = top_k or settings.RAG_TOP_K

    result = await db.execute(select(Snippet))
    all_snippets = result.scalars().all()

    if not all_snippets:
        return []

    query_emb_bytes = embed_text(question)
    scored = []

    for snippet in all_snippets:
        kw = keyword_score(question, snippet.snippet_text)
        sem = 0.0
        if query_emb_bytes and snippet.embedding:
            sem = cosine_sim(query_emb_bytes, snippet.embedding)
        # Hybrid: 40% keyword + 60% semantic
        score = 0.4 * kw + 0.6 * sem
        scored.append((snippet, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


KB_ANSWER_SYSTEM = """Ты — корпоративный ассистент. Отвечай ТОЛЬКО на основе предоставленного контекста.
Если в контексте нет ответа — честно скажи "Данных недостаточно для ответа на этот вопрос." и поставь needs_review=true.
Никогда не придумывай информацию. Возвращай строгий JSON без Markdown-обёртки.

Формат ответа:
{"answer": "...", "sources": [{"quote": "..."}], "confidence": "high|medium|low", "needs_review": false}"""


async def answer_with_sources(
    question: str,
    context_snippets: List[Tuple[Snippet, float]],
    doc_map: dict[str, str] | None = None,
) -> AnswerWithSourcesSchema:
    """Generate answer from retrieved snippets."""
    if not context_snippets:
        return AnswerWithSourcesSchema(
            answer="Данных недостаточно для ответа на этот вопрос.",
            sources=[],
            confidence="low",
            needs_review=True,
        )

    context_text = "\n\n".join(
        f"[Фрагмент {i+1}]: {snip.snippet_text}"
        for i, (snip, _) in enumerate(context_snippets)
    )

    prompt = f"""ВОПРОС: {question}

КОНТЕКСТ (фрагменты из базы знаний):
{context_text}

Ответь строго по контексту. Верни JSON."""

    try:
        raw = await call_llm(prompt, KB_ANSWER_SYSTEM)
        clean = extract_json(raw)
        data = json.loads(clean)
        schema = AnswerWithSourcesSchema(**data)

        # Enrich sources with document info
        if doc_map and schema.sources:
            for i, src in enumerate(schema.sources):
                if i < len(context_snippets):
                    snip, _ = context_snippets[i]
                    src.document_id = snip.document_id
                    src.document_title = doc_map.get(snip.document_id, "")

        # Enforce rule: empty sources → needs_review
        if not schema.sources:
            schema.needs_review = True
            if "недостаточно" not in schema.answer.lower():
                schema.answer = "Данных недостаточно для ответа на этот вопрос."

        return schema

    except (json.JSONDecodeError, ValidationError) as e:
        return AnswerWithSourcesSchema(
            answer="Данных недостаточно для ответа на этот вопрос.",
            sources=[],
            confidence="low",
            needs_review=True,
        )
