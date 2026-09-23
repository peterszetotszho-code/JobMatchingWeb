---
title: Job Fit Assistant
emoji: 💼
sdk: docker
app_port: 7860
license: mit
---

# Job Fit Assistant

> **Repository:** [github.com/peterszetotszho-code/JobMatchingWeb](https://github.com/peterszetotszho-code/JobMatchingWeb)
> **Live demo:** https://slot-collectibles-arise-premiere.trycloudflare.com (temporary Cloudflare Tunnel — may change)

A resume-to-job-description matching tool built with **LLM + RAG**. Upload your resume, paste a job description (e.g. from JobsDB), and the app decomposes the JD into atomic requirements, retrieves supporting evidence from your resume, judges fit per requirement, and outputs a **fit score + a detailed analysis**. It also supports follow-up Q&A with optional live web search.

## Tech Stack
| Part | Tech |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI (REST + SSE streaming) |
| LLM | DeepSeek (`deepseek-flash`, thinking disabled) |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (local, Chinese + English) |
| Web search | DuckDuckGo (free, no API key) |
| File parsing | pypdf / python-docx |

## Architecture
```
React (Vite) ──HTTP/JSON + SSE──▶ FastAPI (api.py) ──▶ matcher / chat ──▶ DeepSeek + local embeddings + DuckDuckGo
```

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

## How it works
1. **Decompose** — the LLM splits the JD into atomic requirements.
2. **Retrieve** — each requirement is embedded and matched against resume chunks (evidence).
3. **Judge** — the LLM judges each requirement (`matched / partial / gap`) using the retrieved evidence.
4. **Score** — a 0–100 fit score is computed deterministically (never asked of the LLM).
5. **Analyze** — the LLM writes a detailed 300+ char analysis (streamed to the UI).

Follow-up Q&A: an LLM router decides whether the question needs local context (resume / JD / analysis) or live web search (DuckDuckGo), then answers in plain Chinese.

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
├── config.py           # settings
├── frontend/           # React + Vite frontend
├── scripts/smoke_test.py
└── data/               # sample resume + JD
```
