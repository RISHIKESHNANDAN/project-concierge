"""Document ingestion: parse front matter, chunk by section, embed, store in ChromaDB.

Updating a single policy does NOT need a rebuild:
    python -m app.ingestion.ingest --file data/documents/returns_policy.md
(deletes that document's old chunks, then re-adds the new ones)
"""
import argparse
import re
from pathlib import Path

from app.config import CHROMA_DIR, COLLECTION, DOCS_DIR, EMBED_MODEL, MAX_CHUNK_CHARS

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    return get_model().encode(texts, normalize_embeddings=True).tolist()


def get_collection(reset: bool = False):
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if reset:
        try:
            client.delete_collection(COLLECTION)
        except Exception:
            pass
    return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def parse_document(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, m.group(2)


def chunk_body(body: str, max_chars: int = MAX_CHUNK_CHARS) -> list[tuple[str, str]]:
    """Split on '## ' headings (policies are organised by section, so a section is a
    self-contained answer). Oversized sections are split on paragraph boundaries."""
    chunks = []
    for sec in re.split(r"(?m)^(?=## )", body):
        sec = sec.strip()
        if not sec:
            continue
        first = sec.splitlines()[0]
        heading = first.lstrip("# ").strip() if first.startswith("#") else "Intro"
        if len(sec) <= max_chars:
            chunks.append((heading, sec))
            continue
        buf = ""
        for para in sec.split("\n\n"):
            if buf and len(buf) + len(para) > max_chars:
                chunks.append((heading, buf.strip()))
                buf = ""
            buf += para + "\n\n"
        if buf.strip():
            chunks.append((heading, buf.strip()))
    return chunks


def upsert_document(path: Path, collection=None) -> int:
    collection = collection or get_collection()
    meta, body = parse_document(Path(path).read_text(encoding="utf-8"))
    doc_id = meta.get("doc_id", Path(path).stem)
    collection.delete(where={"doc_id": doc_id})  # remove stale chunks of this doc
    chunks = chunk_body(body)
    if not chunks:
        return 0
    base = {k: v for k, v in meta.items()}
    base["doc_id"] = doc_id
    base.setdefault("status", "active")
    base.setdefault("visibility", "public")
    base.setdefault("authority", "faq")
    texts = [f"{meta.get('title', doc_id)} - {h}\n{t}" for h, t in chunks]
    collection.add(
        ids=[f"{doc_id}::{i}" for i in range(len(chunks))],
        documents=texts,
        embeddings=embed(texts),
        metadatas=[{**base, "section": h} for h, _ in chunks],
    )
    return len(chunks)


def ingest_all(reset: bool = True) -> int:
    col = get_collection(reset=reset)
    total = 0
    for p in sorted(DOCS_DIR.glob("*.md")):
        n = upsert_document(p, col)
        print(f"{p.name}: {n} chunks")
        total += n
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="rebuild the whole index")
    ap.add_argument("--file", help="re-ingest a single updated document")
    a = ap.parse_args()
    if a.file:
        print(f"{a.file}: {upsert_document(Path(a.file))} chunks")
    else:
        print("total chunks:", ingest_all())
