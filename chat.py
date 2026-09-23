"""Follow-up Q&A: local RAG (resume + JD + analysis) + web search (HK-oriented)."""
from __future__ import annotations

import numpy as np

import config
import llm
import embeddings
import web_search

ROUTER_SYSTEM = """你是求職助手。判斷用戶的問題是否需要「搜尋網際網路」才能回答。

需要聯網：問公司背景／業務、行業資訊、職位行情、薪資行情、外部事實等，本地履歷／JD／分析無法回答的。
不需要聯網：問這次求職分析、履歷怎麼改、JD 要求等，本地資料已足夠。

搜尋關鍵字（query）的規則：
- 一定要以「香港」為主，避免搜到台灣／其他地區的結果。
- 若問題涉及「這家公司／這份工作」，請從 JD 找出公司名稱，關鍵字要包含公司名。
- 範例：問薪資 →「香港 IT 支援 薪資」；問公司業務 →「和記電訊香港 業務」。

只輸出 JSON，不要輸出其他文字。"""

ROUTER_USER = """職位描述（JD，供判斷公司名稱與職位）：
{jd}

用戶問題：{question}

請輸出 JSON：
{{"needs_web": true 或 false, "query": "香港導向的搜尋關鍵字（needs_web=true 時填，否則空字串）"}}"""

ANSWER_SYSTEM = """你是求職助手。請根據提供的背景資料回答用戶問題，回答要具體、有幫助、簡潔，用自然流暢的中文。不要輸出網址、引用標記或多餘格式。只輸出回答文字。"""

ANSWER_USER = """背景資料（履歷／JD／分析相關片段）：
{local}

網頁搜尋結果（僅供參考）：
{web}

用戶問題：{question}

請用自然中文回答（不要附網址或 [網頁N] 標記）。"""


def _build_corpus(resume: str, jd: str, analysis: str) -> list[dict]:
    corpus = []
    for line in resume.splitlines():
        line = line.strip()
        if line:
            corpus.append({"source": "履歷", "text": line})
    for line in jd.splitlines():
        line = line.strip()
        if line:
            corpus.append({"source": "JD", "text": line})
    if analysis:
        corpus.append({"source": "分析", "text": analysis})
    return corpus


def _retrieve(question: str, corpus: list[dict], top_k: int = 6) -> list[dict]:
    if not corpus:
        return []
    qvec = embeddings.embed([question])
    cvecs = embeddings.embed([c["text"] for c in corpus])
    sim = (qvec @ cvecs.T)[0]
    order = np.argsort(sim)[::-1][:top_k]
    return [corpus[i] for i in order]


def _route(question: str, jd: str) -> tuple[bool, str]:
    data = llm.chat_json(ROUTER_SYSTEM, ROUTER_USER.format(question=question, jd=jd))
    if isinstance(data, dict):
        return bool(data.get("needs_web", False)), data.get("query", "") or question
    return False, ""


def _answer_text(question: str, local: list[dict], web: list[dict]) -> str:
    local_txt = "\n".join(f"[{c['source']}] {c['text']}" for c in local) or "（無）"
    web_txt = "\n".join(f"- {r['title']}：{r['snippet']}" for r in web) or "（無）"
    return ANSWER_USER.format(local=local_txt, web=web_txt, question=question)


def ask_question(question: str, resume: str, jd: str, analysis: str) -> dict:
    """Non-streaming: returns {answer, needs_web, web_sources, local_sources}."""
    corpus = _build_corpus(resume, jd, analysis)
    local = _retrieve(question, corpus)
    needs_web, query = _route(question, jd)
    web = web_search.search(query) if needs_web else []
    answer = llm.chat(ANSWER_SYSTEM, _answer_text(question, local, web)).strip()
    return {
        "answer": answer,
        "needs_web": needs_web,
        "web_sources": web,
        "local_sources": [c["text"] for c in local],
    }


def ask_question_stream(question: str, resume: str, jd: str, analysis: str):
    """Streaming variant: yields event dicts (stage / chunk / result)."""
    yield {"type": "stage", "message": "檢索相關資料…"}
    corpus = _build_corpus(resume, jd, analysis)
    local = _retrieve(question, corpus)

    yield {"type": "stage", "message": "判斷是否需要聯網…"}
    needs_web, query = _route(question, jd)

    web = []
    if needs_web:
        yield {"type": "stage", "message": "搜尋網頁…"}
        web = web_search.search(query)

    yield {"type": "stage", "message": "生成回答…"}
    parts = []
    for chunk in llm.chat_stream(ANSWER_SYSTEM, _answer_text(question, local, web)):
        parts.append(chunk)
        yield {"type": "chunk", "text": chunk}

    yield {"type": "result", "data": {"answer": "".join(parts), "web_sources": web}}
