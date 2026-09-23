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


@asynccontextmanager
async def lifespan(_: FastAPI):
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


# Serve the built React frontend (if present) so a single server hosts the whole site.
# Note: /api/* routes are registered first, so they take precedence over this mount.
_FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
