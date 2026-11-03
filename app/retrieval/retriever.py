import re

from app.config import RETRIEVAL_MODE, TOP_K
from app.ingestion.ingest import embed, get_collection

PUBLIC_ACTIVE = {"$and": [{"status": {"$eq": "active"}}, {"visibility": {"$eq": "public"}}]}


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9$.]+", s.lower()))


def retrieve(query: str, k: int = TOP_K, mode: str = RETRIEVAL_MODE, include_all: bool = False) -> list[dict]:
    """Superseded and internal documents are filtered out at query time (include_all=True is
    for diagnostics only). mode='hybrid' reranks dense hits with keyword overlap."""
    col = get_collection()
    n = k * 3 if mode == "hybrid" else k
    res = col.query(query_embeddings=embed([query]), n_results=n,
                    where=None if include_all else PUBLIC_ACTIVE)
    out = []
    q = _tokens(query)
    for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        overlap = len(q & _tokens(text)) / max(len(q), 1)
        score = (1 - dist) + (0.5 * overlap if mode == "hybrid" else 0)
        out.append({"text": text, "meta": meta, "distance": dist, "score": score})
    out.sort(key=lambda p: p["score"], reverse=True)
    return out[:k]
