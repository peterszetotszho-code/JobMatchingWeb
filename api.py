"""FastAPI backend: expose the job-fit assistant as a REST API."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import chat
import embeddings
import matcher
import resume_io
import store


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init()
    embeddings.warmup()  # preload the embedding model at startup to avoid cold start on first analysis
    yield


app = FastAPI(title="Job Fit Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only; restrict to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    resume: str
    jd: str


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/parse")
async def parse_file(file: UploadFile = File(...)) -> dict:
    """Upload a PDF/DOCX/TXT file and return the extracted text."""
    data = await file.read()
    return {"text": resume_io.extract_bytes(data, file.filename or "")}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    """Non-streaming: return the full result at once."""
    result = matcher.analyze(req.resume, req.jd)
    if "error" in result:
        return {"error": result["error"]}
    return result


@app.post("/api/analyze/stream")
def analyze_stream(req: AnalyzeRequest) -> StreamingResponse:
    """Streaming (SSE): stage messages, then the analysis text token-by-token, then the metrics."""

    def gen():
        try:
            for event in matcher.analyze_stream(req.resume, req.jd):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


class AskRequest(BaseModel):
    question: str
    resume: str
    jd: str
    analysis: str


@app.post("/api/ask")
def ask(req: AskRequest) -> dict:
    """Follow-up Q&A (non-streaming): local RAG + web search."""
    return chat.ask_question(req.question, req.resume, req.jd, req.analysis)


@app.post("/api/ask/stream")
def ask_stream(req: AskRequest) -> StreamingResponse:
    """Follow-up Q&A (streaming SSE)."""

    def gen():
        try:
            for event in chat.ask_question_stream(req.question, req.resume, req.jd, req.analysis):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------- Match history (per-user records) ----------

class SaveRecordRequest(BaseModel):
    user_id: str
    resume: str
    jd: str
    analysis: str
    fit_score: int
    matched: int
    partial: int
    gap: int


class AddMessageRequest(BaseModel):
    user_id: str
    role: str
    content: str


@app.post("/api/records")
def save_record(req: SaveRecordRequest) -> dict:
    """Save a completed analysis as a history record."""
    rid = store.save_record(
        req.user_id, req.resume, req.jd, req.analysis,
        req.fit_score, req.matched, req.partial, req.gap,
    )
    return {"record_id": rid}


@app.get("/api/records")
def list_records(user_id: str) -> dict:
    """List a user's history records (newest first, no heavy fields)."""
    return {"records": store.list_records(user_id)}


@app.get("/api/records/{record_id}")
def get_record(record_id: int, user_id: str) -> dict:
    """Get a full record (with messages) if it belongs to the user."""
    rec = store.get_record(user_id, record_id)
    if rec is None:
        return {"error": "record not found"}
    return rec


@app.delete("/api/records/{record_id}")
def delete_record(record_id: int, user_id: str) -> dict:
    """Delete a record (and its messages) if it belongs to the user."""
    return {"deleted": store.delete_record(user_id, record_id)}


@app.post("/api/records/{record_id}/messages")
def add_message(record_id: int, req: AddMessageRequest) -> dict:
    """Append a chat message to a record (ownership-checked)."""
    if store.get_record(req.user_id, record_id) is None:
        return {"error": "record not found"}
    return {"message_id": store.add_message(record_id, req.role, req.content)}


# Serve the built React frontend (if present) so a single server hosts the whole site.
# Note: /api/* routes are registered first, so they take precedence over this mount.
_FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
