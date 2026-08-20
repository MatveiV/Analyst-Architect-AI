"""
Shared embedding utilities — sentence-transformers + FAISS index.
Used by rag_engine.py and memory_service.py.
"""
import pickle
import re
from typing import List, Optional, Tuple
import numpy as np

_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _embed_model = None
    return _embed_model


def embed_text(text: str) -> Optional[bytes]:
    model = _get_embed_model()
    if model is None:
        return None
    vec = model.encode(text, normalize_embeddings=True)
    return pickle.dumps(vec.tolist())


def embed_text_to_array(text: str) -> Optional[np.ndarray]:
    model = _get_embed_model()
    if model is None:
        return None
    return model.encode(text, normalize_embeddings=True)


def cosine_sim(a_bytes: bytes, b_bytes: bytes) -> float:
    try:
        a = np.array(pickle.loads(a_bytes))
        b = np.array(pickle.loads(b_bytes))
        return float(np.dot(a, b))
    except Exception:
        return 0.0


def array_to_bytes(vec: np.ndarray) -> bytes:
    return pickle.dumps(vec.tolist())


def bytes_to_array(data: bytes) -> np.ndarray:
    return np.array(pickle.loads(data))


def keyword_score(query: str, text: str) -> float:
    query_words = set(re.findall(r"\w+", query.lower()))
    text_words = set(re.findall(r"\w+", text.lower()))
    if not query_words:
        return 0.0
    return len(query_words & text_words) / len(query_words)


def hybrid_score(
    query: str,
    text: str,
    query_emb_bytes: Optional[bytes],
    text_emb_bytes: Optional[bytes],
    kw_weight: float = 0.4,
    sem_weight: float = 0.6,
) -> float:
    kw = keyword_score(query, text)
    sem = 0.0
    if query_emb_bytes and text_emb_bytes:
        sem = cosine_sim(query_emb_bytes, text_emb_bytes)
    return kw_weight * kw + sem_weight * sem


# ── FAISS index ──────────────────────────────────────────────────────────────

_faiss_index = None
_faiss_ids: List[str] = []


def _faiss_available() -> bool:
    try:
        import faiss  # noqa
        return True
    except ImportError:
        return False


def build_faiss_index(embeddings: List[Tuple[str, bytes]]):
    global _faiss_index, _faiss_ids
    _faiss_index = None
    _faiss_ids = []

    if not _faiss_available() or not embeddings:
        return

    import faiss

    dim = len(bytes_to_array(embeddings[0][1]))
    index = faiss.IndexFlatIP(dim)
    ids: List[str] = []
    vecs: List[np.ndarray] = []

    for item_id, emb_bytes in embeddings:
        vec = bytes_to_array(emb_bytes)
        if vec.shape[0] != dim:
            continue
        vecs.append(vec)
        ids.append(item_id)

    if not vecs:
        return

    matrix = np.array(vecs).astype(np.float32)
    index.add(matrix)
    _faiss_index = index
    _faiss_ids = ids


def add_to_faiss_index(item_id: str, emb_bytes: bytes):
    global _faiss_index, _faiss_ids
    if _faiss_index is None or not _faiss_available():
        return

    import faiss

    vec = bytes_to_array(emb_bytes).astype(np.float32).reshape(1, -1)
    _faiss_index.add(vec)
    _faiss_ids.append(item_id)


def search_faiss(query_emb_bytes: bytes, top_k: int = 10) -> List[Tuple[str, float]]:
    if _faiss_index is None or not _faiss_available():
        return []

    import faiss

    query_vec = bytes_to_array(query_emb_bytes).astype(np.float32).reshape(1, -1)
    scores, indices = _faiss_index.search(query_vec, top_k)
    results: List[Tuple[str, float]] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0 and idx < len(_faiss_ids):
            results.append((_faiss_ids[idx], float(score)))
    return results
