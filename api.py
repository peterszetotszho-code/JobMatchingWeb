"""FastAPI 後端：把求職助手包成 REST API。"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import embeddings
import matcher
import resume_io


@asynccontextmanager
async def lifespan(_: FastAPI):
    embeddings.warmup()  # 啟動時預先載入 embedding 模型，避免首次分析冷啟動
    yield


app = FastAPI(title="求職助手 Job Fit Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開發用；正式部署請改成前端網域
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
    """上傳 PDF/DOCX/TXT，回傳抽取出的文字。"""
    data = await file.read()
    return {"text": resume_io.extract_bytes(data, file.filename or "")}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    """非串流：一次性回傳完整結果。"""
    result = matcher.analyze(req.resume, req.jd)
    if "error" in result:
        return {"error": result["error"]}
    return result


@app.post("/api/analyze/stream")
def analyze_stream(req: AnalyzeRequest) -> StreamingResponse:
    """串流（SSE）：先回傳階段訊息，再逐字串流分析文字，最後回傳指標。"""

    def gen():
        try:
            for event in matcher.analyze_stream(req.resume, req.jd):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# 掛載已 build 的 React 前端（若存在），單一伺服器即可服務整站。
# 注意：/api/* 路由先註冊，優先於此掛載，所以不會被靜態檔蓋掉。
_FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
