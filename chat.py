"""求職追問：本地 RAG（履歷 + JD + 分析）+ 聯網搜尋的問答。"""
from __future__ import annotations

import numpy as np

import config
import llm
import embeddings
import web_search

ROUTER_SYSTEM = """你是求職助手。判斷用戶的問題是否需要「搜尋網際網路」才能回答。

需要聯網：問公司背景／業務、行業資訊、職位行情、外部事實等，本地履歷／JD／分析無法回答的。
不需要聯網：問這次求職分析、履歷怎麼改、JD 要求等，本地資料已足夠。

只輸出 JSON，不要輸出其他文字。"""

ROUTER_USER = """用戶問題：{question}

請輸出 JSON：
{{"needs_web": true 或 false, "query": "要搜尋的關鍵字（needs_web=true 時填，否則空字串）"}}"""

ANSWER_SYSTEM = """你是求職助手。請根據提供的背景資料回答用戶問題，回答要具體、有幫助、簡潔。引用網頁資料時用 [網頁1] 這類標註。只輸出回答文字，不要其他。"""

ANSWER_USER = """背景資料（履歷／JD／分析相關片段）：
{local}

網頁搜尋結果：
{web}

用戶問題：{question}

請回答（用中文，簡潔具體）。"""


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


def _route(question: str) -> tuple[bool, str]:
    data = llm.chat_json(ROUTER_SYSTEM, ROUTER_USER.format(question=question))
    if isinstance(data, dict):
        return bool(data.get("needs_web", False)), data.get("query", "") or question
    return False, ""


def _answer_text(question: str, local: list[dict], web: list[dict]) -> str:
    local_txt = "\n".join(f"[{c['source']}] {c['text']}" for c in local) or "（無）"
    web_txt = "\n".join(
        f"[網頁{i + 1}] {r['title']}：{r['snippet']} ({r['url']})" for i, r in enumerate(web)
    ) or "（無）"
    return ANSWER_USER.format(local=local_txt, web=web_txt, question=question)


def ask_question(question: str, resume: str, jd: str, analysis: str) -> dict:
    """非串流：回傳 {answer, needs_web, web_sources, local_sources}。"""
    corpus = _build_corpus(resume, jd, analysis)
    local = _retrieve(question, corpus)
    needs_web, query = _route(question)
    web = web_search.search(query) if needs_web else []
    answer = llm.chat(ANSWER_SYSTEM, _answer_text(question, local, web)).strip()
    return {
        "answer": answer,
        "needs_web": needs_web,
        "web_sources": web,
        "local_sources": [c["text"] for c in local],
    }


def ask_question_stream(question: str, resume: str, jd: str, analysis: str):
    """串流版：yield 事件 dict（stage / chunk / result）。"""
    yield {"type": "stage", "message": "檢索相關資料…"}
    corpus = _build_corpus(resume, jd, analysis)
    local = _retrieve(question, corpus)

    yield {"type": "stage", "message": "判斷是否需要聯網…"}
    needs_web, query = _route(question)

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
