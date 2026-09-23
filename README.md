# 求職助手 Job Fit Assistant

一個以 **LLM + RAG** 打造的求職比對工具：上傳你的履歷，貼上求職網站（JobsDB）的職位描述（JD），系統會把 JD 拆解成逐條要求，逐一檢索你的履歷、判斷符合度，並以**可追溯的證據（引用履歷原文）**呈現結果。

A resume-to-JD matching tool built with LLM + RAG. Upload your resume, paste a job description (e.g. from JobsDB), and the app decomposes the JD into atomic requirements, retrieves supporting evidence from your resume, and returns a fit score with **traceable citations**.

## 功能 Features
- JD 自動拆解為逐條可核對要求（技能／經驗／學歷／語言／軟技能）
- 本機 Embedding（BGE-M3，多語言：繁體中文 + 英文，離線零成本）
- 混合判斷：向量檢索找差距，模糊案例交給 LLM 裁決
- 輸出：符合度分數、逐條判決（匹配／部分／缺口）、履歷原文證據
- 介面：Streamlit（繁體中文 + 英文）

## 技術棧 Tech Stack
| 部分 | 技術 |
|---|---|
| LLM | DeepSeek（`deepseek-flash`，OpenAI 相容 API） |
| Embedding | `BAAI/bge-m3`（sentence-transformers，本機） |
| 介面 | Streamlit |
| 語言 | Python 3.11+ |

## 安裝 Setup
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
# 方法 1：環境變數
set DEEPSEEK_API_KEY=sk-xxxx        # Windows cmd
export DEEPSEEK_API_KEY=sk-xxxx     # bash

# 方法 2：複製 .env.example 為 .env 並填入 key
```

## 執行 Run
```bash
streamlit run app.py
```

## 自檢 Smoke test
```bash
python scripts/smoke_test.py
```

## 運作原理 How it works
1. **拆解**：LLM 把 JD 拆成原子要求。
2. **檢索**：每條要求用 BGE-M3 與履歷片段做 cosine similarity，取 top-k 當證據。
3. **判斷**：高相似 = 匹配；低相似 = 缺口；介於中間交給 LLM 裁決。
4. **打分**：以確定性方式計算 0–100 分，避免直接問 LLM 要數字（不可重現）。
5. **呈現**：逐條判決 + 引用履歷原文，保留可追溯性。

## 資料夾結構 Project structure
```
RAG Trail/
├── app.py              # Streamlit 介面（繁中 + 英文）
├── config.py           # 模型、閾值等設定
├── llm.py              # DeepSeek 客戶端
├── embeddings.py       # 本機 BGE-M3 embedding
├── matcher.py          # 核心：拆解 → 檢索 → 判斷 → 打分
├── resume_io.py        # PDF / DOCX / 文字抽取
├── scripts/smoke_test.py
├── data/               # 範例履歷 + JD
└── requirements.txt
```
