"""
RAG Engine — гибридный поиск по базе знаний.
Keyword search + косинусное сходство эмбеддингов.

Эпик A5: собственный FAISS-индекс для Snippet (отдельный от индекса memory_service,
который использует те же общие faiss-примитивы из embeddings.py для другой таблицы —
общий модульный индекс из embeddings.py нельзя переиспользовать напрямую, иначе
перезапись индекса одним потребителем стирала бы индекс другого).
"""
import json
import re
import uuid
from typing import List, Tuple
import numpy as np
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.snippet import Snippet
from app.models.document import Document
from app.schemas import AnswerWithSourcesSchema, SourceItem
from app.services.llm_client import call_llm, extract_json
from app.services.embeddings import (
    embed_text, cosine_sim, keyword_score, bytes_to_array, _faiss_available,
)

# Pre-existing bug fix: tests/test_main.py imports `_keyword_score` from this module,
# but it was only ever defined in embeddings.py as `keyword_score` (no underscore prefix,
# different module). Alias kept for backward-compat with the existing test suite.
_keyword_score = keyword_score

# ── Эпик A5: локальный (не разделяемый с memory_service) FAISS-индекс по Snippet ──
_snippet_faiss_index = None
_snippet_faiss_ids: List[str] = []


async def rebuild_snippet_faiss_index(db: AsyncSession) -> int:
    """Полная пересборка индекса по всем Snippet с непустым embedding.
    Вызывается на старте приложения (main.py lifespan) и после /kb/reindex."""
    global _snippet_faiss_index, _snippet_faiss_ids
    _snippet_faiss_index = None
    _snippet_faiss_ids = []

    if not _faiss_available():
        return 0

    result = await db.execute(select(Snippet).where(Snippet.embedding.isnot(None)))
    snippets = result.scalars().all()
    if not snippets:
        return 0

    import faiss
    vecs, ids = [], []
    dim = None
    for s in snippets:
        try:
            vec = bytes_to_array(s.embedding).astype(np.float32)
        except Exception:
            continue
        if dim is None:
            dim = vec.shape[0]
        if vec.shape[0] != dim:
            continue
        vecs.append(vec)
        ids.append(s.id)

    if not vecs:
        return 0

    index = faiss.IndexFlatIP(dim)
    index.add(np.array(vecs).astype(np.float32))
    _snippet_faiss_index = index
    _snippet_faiss_ids = ids
    return len(ids)


def _add_snippet_to_faiss(snippet_id: str, emb_bytes: bytes) -> None:
    """Инкрементальное добавление одного snippet без полной пересборки индекса."""
    global _snippet_faiss_index, _snippet_faiss_ids
    if not _faiss_available() or _snippet_faiss_index is None or not emb_bytes:
        return
    try:
        vec = bytes_to_array(emb_bytes).astype(np.float32).reshape(1, -1)
        if vec.shape[1] != _snippet_faiss_index.d:
            return  # размерность не совпадает с индексом — пропускаем, дождётся полной пересборки
        _snippet_faiss_index.add(vec)
        _snippet_faiss_ids.append(snippet_id)
    except Exception:
        pass


def _search_snippet_faiss(query_emb_bytes: bytes, top_k: int) -> List[Tuple[str, float]]:
    if _snippet_faiss_index is None or not _faiss_available() or not query_emb_bytes:
        return []
    query_vec = bytes_to_array(query_emb_bytes).astype(np.float32).reshape(1, -1)
    scores, indices = _snippet_faiss_index.search(query_vec, top_k)
    out = []
    for score, idx in zip(scores[0], indices[0]):
        if 0 <= idx < len(_snippet_faiss_ids):
            out.append((_snippet_faiss_ids[idx], float(score)))
    return out


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
        if emb:
            # Эпик A5: инкрементально в FAISS, полная пересборка не нужна на каждый документ
            _add_snippet_to_faiss(snippet.id, emb)
    await db.commit()





async def retrieve_snippets(
    db: AsyncSession, question: str, top_k: int | None = None
) -> List[Tuple[Snippet, float]]:
    """Hybrid retrieval: keyword + semantic similarity.

    Эпик A5: если FAISS-индекс собран, сначала сужаем кандидатов приближённым поиском
    (IndexFlatIP — точный поиск, не approximate, так что порядок детерминирован), а затем
    досчитываем гибридный score (keyword+semantic) только по кандидатам — вместо полного
    скана таблицы snippets на каждый вопрос, что не масштабируется на растущую базу знаний.
    """
    k = top_k or settings.RAG_TOP_K
    query_emb_bytes = embed_text(question)

    if _snippet_faiss_index is not None and query_emb_bytes:
        hits = _search_snippet_faiss(query_emb_bytes, top_k=max(k * 3, 20))
        candidate_ids = [h[0] for h in hits]
        if not candidate_ids:
            return []
        result = await db.execute(select(Snippet).where(Snippet.id.in_(candidate_ids)))
        candidates = result.scalars().all()
    else:
        # Fallback: полный скан (маленькая БД или FAISS недоступен в окружении)
        result = await db.execute(select(Snippet))
        candidates = result.scalars().all()

    if not candidates:
        return []

    scored = []
    for snippet in candidates:
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
