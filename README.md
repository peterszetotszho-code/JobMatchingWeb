# 求職助手 Job Fit Assistant

一個以 **LLM + RAG** 打造的求職比對工具：上傳履歷，貼上求職網站（JobsDB）的職位描述（JD），系統會把 JD 拆成逐條要求、逐條檢索履歷證據並判斷符合度，最後輸出**符合度分數 + 詳細分析**。

A resume-to-JD matching tool built with LLM + RAG. Upload your resume, paste a job description (e.g. from JobsDB), and get a fit score plus a detailed, traceable analysis.

## 技術棧 Tech Stack
| 部分 | 技術 |
|---|---|
| 前端 | React + Vite |
| 後端 | FastAPI（REST + SSE 串流） |
| LLM | DeepSeek（`deepseek-flash`，關閉 thinking 加速） |
| Embedding | `paraphrase-multilingual-MiniLM-L12-v2`（本機，繁中 + 英文） |
| 檔案解析 | pypdf / python-docx |

## 架構 Architecture
```
React 前端 (Vite) ──HTTP/JSON + SSE──▶ FastAPI (api.py) ──▶ matcher ──▶ DeepSeek + 本機 embedding
```

## 安裝 Setup

### 後端 Backend
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```
設定 DeepSeek API key（擇一）：
```bash
set DEEPSEEK_API_KEY=sk-xxxx        # Windows cmd
export DEEPSEEK_API_KEY=sk-xxxx     # bash
# 或複製 .env.example 為 .env 並填入 key
```

### 前端 Frontend
```bash
cd frontend
npm install
```

## 執行 Run

### 方式一：單一伺服器（先 build 前端）
```bash
cd frontend && npm run build && cd ..
.venv\Scripts\python -m uvicorn api:app --host 127.0.0.1 --port 8000
# 開啟 http://localhost:8000（FastAPI 同時服務 API 與前端）
```

### 方式二：開發模式（前後端分離、前端熱更新）
```bash
# 終端 1 —— 後端
.venv\Scripts\python -m uvicorn api:app --reload --port 8000

# 終端 2 —— 前端
cd frontend && npm run dev
# 開啟 http://localhost:5173（Vite 會把 /api proxy 到 8000）
```

## API 端點
| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/api/health` | 健康檢查 |
| POST | `/api/parse` | 上傳 PDF/DOCX/TXT，回傳抽取文字 |
| POST | `/api/analyze` | 完整分析（非串流，一次回傳） |
| POST | `/api/analyze/stream` | 串流分析（SSE：階段訊息 → 逐字分析 → 指標） |

## 自檢 Smoke test
```bash
python scripts/smoke_test.py
```

## 運作原理 How it works
1. **拆解**：LLM 把 JD 拆成原子要求。
2. **檢索**：每條要求用本機 embedding 檢索履歷片段當證據。
3. **判斷**：LLM 依證據逐條判 `matched / partial / gap`。
4. **打分**：以確定性方式算 0–100 分（不直接問 LLM 要數字）。
5. **分析**：LLM 生成 300+ 字詳細分析（支援串流逐字顯示）。

## 資料夾結構 Project structure
```
RAG Trail/
├── api.py              # FastAPI 後端（REST + SSE）
├── matcher.py          # 核心：拆解 → 檢索 → 判斷 → 打分 → 分析
├── llm.py              # DeepSeek 客戶端（含串流）
├── embeddings.py       # 本機 embedding
├── resume_io.py        # PDF / DOCX / 文字抽取
├── config.py           # 模型、閾值等設定
├── app.py              # （舊）Streamlit 版，已由 frontend 取代
├── frontend/           # React + Vite 前端
├── scripts/smoke_test.py
└── data/               # 範例履歷 + JD
```
