---
title: Job Fit Assistant
emoji: 💼
sdk: docker
app_port: 7860
license: mit
---

# Job Fit Assistant

> **Repository:** [github.com/peterszetotszho-code/JobMatchingWeb](https://github.com/peterszetotszho-code/JobMatchingWeb)

A **resume-to-job-description matching tool** for the Hong Kong job market, powered by **LLM + RAG**. Paste a job description (e.g. from JobsDB), upload your resume, and the app decomposes the JD into atomic requirements, retrieves supporting evidence from your resume, judges your fit against each requirement, and returns a **fit score plus a detailed, human-readable analysis**. It also supports follow-up Q&A with optional live web search, and keeps a private per-user match history.

## Features

- **📄 Resume + JD input** — paste text or upload PDF / DOCX / TXT files.
- **🔍 RAG matching** — a `decompose → retrieve → judge → score` pipeline; the LLM judges each requirement against retrieved resume evidence rather than relying on a naive similarity threshold.
- **📊 Fit score + analysis** — a deterministic 0–100 score plus a 300+ word Chinese analysis, streamed token-by-token to the UI.
- **💬 Follow-up Q&A** — an LLM router decides whether to answer from local context (resume / JD / analysis) or live web search (DuckDuckGo, Hong Kong-oriented).
- **📂 Match history** — per-user records (SQLite) with LLM-generated job titles on the left sidebar; continue a conversation, reload a CV/JD into the inputs, or delete a record.
- **🌏 Bilingual UI** — Traditional Chinese + English, tailored for the Hong Kong market.
- **🚀 Single-server deploy** — FastAPI serves both the REST/SSE API and the built React frontend; ships with a Dockerfile for cloud deployment.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI (REST + SSE streaming) |
| LLM | DeepSeek (`deepseek-flash`, thinking disabled for low latency) |
| Embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (local, Chinese + English) |
| Web search | DuckDuckGo via `ddgs` (free, no API key) |
| File parsing | `pypdf` / `python-docx` |
| Storage | SQLite (stdlib, per-user records) |
| Deployment | Docker (multi-stage build) → Hugging Face Spaces |

## Architecture

```
React (Vite) ──HTTP/JSON + SSE──▶ FastAPI (api.py) ──▶ matcher / chat ──▶ DeepSeek + local embeddings + DuckDuckGo
```

## How it works

1. **Decompose** — the LLM splits the JD into atomic, independently-checkable requirements (plus a one-line job title).
2. **Retrieve** — each requirement is embedded and matched against resume line-chunks to gather citable evidence.
3. **Judge** — the LLM judges each requirement (`matched / partial / gap`) using the retrieved evidence.
4. **Score** — a 0–100 fit score is computed deterministically (never asked of the LLM).
5. **Analyze** — the LLM writes a detailed 300+ word analysis, streamed to the UI.

Follow-up Q&A: an LLM router decides whether a question needs local context (resume / JD / analysis) or live web search (DuckDuckGo, Hong Kong-oriented), then answers in plain Chinese.

## Setup

### Backend
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```
Set your DeepSeek API key (either):
```bash
set DEEPSEEK_API_KEY=sk-xxxx        # Windows cmd
export DEEPSEEK_API_KEY=sk-xxxx     # bash
# or copy .env.example to .env and fill in the key
```

### Frontend
```bash
cd frontend
npm install
```

## Run

### Option 1: single server (build frontend first)
```bash
cd frontend && npm run build && cd ..
.venv\Scripts\python -m uvicorn api:app --host 127.0.0.1 --port 8000
# open http://localhost:8000 (FastAPI serves both the API and the frontend)
```

### Option 2: dev mode (hot-reload frontend)
```bash
# terminal 1 — backend
.venv\Scripts\python -m uvicorn api:app --reload --port 8000

# terminal 2 — frontend
cd frontend && npm run dev
# open http://localhost:5173 (Vite proxies /api to :8000)
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/parse` | Upload PDF/DOCX/TXT, return extracted text |
| POST | `/api/analyze` | Full analysis (non-streaming) |
| POST | `/api/analyze/stream` | Streaming analysis (SSE) |
| POST | `/api/ask` | Follow-up Q&A (non-streaming) |
| POST | `/api/ask/stream` | Follow-up Q&A (SSE) |
| POST | `/api/records` | Save a completed analysis as a history record |
| GET | `/api/records` | List a user's history records |
| GET | `/api/records/{id}` | Get a full record (with messages) |
| DELETE | `/api/records/{id}` | Delete a record and its messages |
| POST | `/api/records/{id}/messages` | Append a chat message to a record |

## Project structure

```
RAG Trail/
├── api.py              # FastAPI backend (REST + SSE)
├── matcher.py          # core: decompose → retrieve → judge → score → analyze
├── chat.py             # follow-up Q&A (local RAG + web search)
├── web_search.py       # DuckDuckGo search (HK-oriented)
├── llm.py              # DeepSeek client (incl. streaming)
├── embeddings.py       # local embeddings
├── resume_io.py        # PDF / DOCX / text extraction
├── store.py            # SQLite persistence for per-user match history
├── config.py           # settings
├── frontend/           # React + Vite frontend
├── Dockerfile          # multi-stage build for cloud deployment
├── scripts/smoke_test.py
└── data/               # sample resume + JD
```
