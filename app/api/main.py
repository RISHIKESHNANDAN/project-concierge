"""Run: uvicorn app.api.main:app --port 8000"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import DOCS_DIR
from app.ingestion.ingest import upsert_document
from app.services.concierge import handle

app = FastAPI(title="Project Concierge")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    customer_email: str  # in production this comes from the authenticated session, never from the message


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat")
def chat(req: ChatRequest):
    return handle(req.message, req.customer_email)


@app.post("/admin/reindex/{filename}")
def reindex(filename: str):
    """Hot-update one policy file without rebuilding the index. (Add real admin auth before production.)"""
    path = (DOCS_DIR / Path(filename).name)
    if not path.exists():
        raise HTTPException(404, "document not found")
    return {"file": path.name, "chunks": upsert_document(path)}
