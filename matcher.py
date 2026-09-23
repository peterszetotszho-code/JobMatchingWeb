"""核心邏輯：JD 拆解 → 逐條檢索證據 → LLM 逐條判斷 → 確定性打分。"""
from __future__ import annotations

import numpy as np

import config
import llm
import embeddings

# ---------- 提示詞（繁體中文 + 英文，配合香港市場） ----------

DECOMPOSE_SYSTEM = """你是一位熟悉香港就業市場的招聘顧問。請把求職者提供的「職位描述（JD）」拆解成一條條「可獨立核對的錄取要求」。

規則：
- 每條要求必須具體、單一，例如「具備 3 年以上 Python 開發經驗」，不要合併多項。
- 只保留「要求」，忽略公司福利、薪金、地點、公司簡介、聯絡方式等非要求內容。
- 保留原文語言（中英夾雜就照原樣）。
- category 只能是下列之一：skills(技能)、experience(經驗)、education(學歷)、language(語言)、soft(軟技能/其他)。

只輸出 JSON，不要輸出其他文字。"""

DECOMPOSE_USER = "職位描述（JD）：\n\n{jd}"

JUDGE_SYSTEM = """你是招聘顧問。以下會列出多條「職位要求」，以及為每條要求「檢索」到的候選人履歷片段。請逐條判斷候選人是否滿足。

判斷標準：
- matched：履歷證據明確支持該要求
- partial：部分相關、或相關但不足
- gap：履歷證據無法支持該要求（含完全沒提到）

每條都要給 verdict 與 reason；reason 用一句話（最多 15 字），盡量引用履歷原文作為證據。

另外輸出 analysis：用自然流暢的中文寫一段**至少 300 字**的詳細分析，具體說明候選人符合了哪些要求（舉出對應技能或經驗）、哪些只部分符合、哪些明顯欠缺，並簡要解釋原因；內容要具體充實、避免空洞。

只輸出 JSON，不要輸出其他文字。"""

JUDGE_USER = """職位要求與檢索到的履歷證據：

{items}

請輸出 JSON（verdict 只能是 matched / partial / gap 三者之一）：
{{"analysis": "詳細分析（至少 300 字）", "judgments": [{{"id": 1, "verdict": "matched", "reason": "一句話說明"}}]}}"""


# ---------- 資料處理 ----------

def decompose_jd(jd_text: str) -> list[dict]:
    """用 LLM 把 JD 拆成原子要求。"""
    user = DECOMPOSE_USER.format(jd=jd_text)
    data = llm.chat_json(DECOMPOSE_SYSTEM, user)
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        raw = data.get("requirements") or data.get("items") or []
    else:
        raw = []
    return [_normalize_requirement(item, i + 1) for i, item in enumerate(raw)]


def _normalize_requirement(item, idx: int) -> dict:
    """把 LLM 回傳的各種欄位名（requirement / text / description…）正規化。"""
    if isinstance(item, str):
        return {"id": idx, "category": "other", "requirement": item}
    text = (
        item.get("requirement")
        or item.get("text")
        or item.get("description")
        or item.get("content")
        or ""
    )
    return {
        "id": item.get("id", idx),
        "category": item.get("category", "other"),
        "requirement": text,
    }


def chunk_resume(text: str) -> list[dict]:
    """把履歷按行切成片段（每一行就是一個可被引用的證據單位）。"""
    chunks = []
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        chunks.append({"id": i, "text": line})
    return chunks


def analyze(resume_text: str, jd_text: str) -> dict:
    """完整流程：拆解 JD → 檢索證據 → LLM 逐條判斷 → 確定性打分。"""
    requirements = decompose_jd(jd_text)
    if not requirements:
        return {"error": "無法從 JD 拆解出要求", "requirements": []}

    resume_chunks = chunk_resume(resume_text)
    if not resume_chunks:
        return {"error": "履歷為空", "requirements": []}

    req_texts = [r["requirement"] for r in requirements]
    chunk_texts = [c["text"] for c in resume_chunks]

    req_vecs = embeddings.embed(req_texts)          # (n_req, dim)
    chunk_vecs = embeddings.embed(chunk_texts)      # (n_chunk, dim)
    sim = req_vecs @ chunk_vecs.T                   # (n_req, n_chunk) = cosine

    # 每條要求檢索 top-k 履歷片段作為證據（供 LLM 判斷 + 引用）
    evidence_map = {}
    best_sim_map = {}
    for i in range(len(requirements)):
        order = np.argsort(sim[i])[::-1][: config.TOP_K]
        evidence_map[i] = [resume_chunks[j]["text"] for j in order]
        best_sim_map[i] = float(sim[i][order[0]])

    judgments, analysis = _judge_all(requirements, evidence_map)

    results = []
    for i, req in enumerate(requirements):
        rid = req.get("id", i + 1)
        j = judgments.get(rid, {"verdict": "partial", "reason": ""})
        results.append({
            "id": rid,
            "category": req.get("category", "other"),
            "requirement": req["requirement"],
            "verdict": j["verdict"],
            "reason": j["reason"],
            "evidence": evidence_map[i],
            "score": round(best_sim_map[i], 4),
        })

    return {
        "fit_score": _compute_score(results),
        "analysis": analysis,
        "requirements": results,
        "matched": sum(1 for r in results if r["verdict"] == "matched"),
        "partial": sum(1 for r in results if r["verdict"] == "partial"),
        "gap": sum(1 for r in results if r["verdict"] == "gap"),
    }


def _judge_all(requirements: list[dict], evidence_map: dict) -> tuple[dict, str]:
    """一次 LLM 呼叫判斷所有要求，並回傳 (judgments, analysis)。"""
    lines = []
    for i, req in enumerate(requirements):
        rid = req.get("id", i + 1)
        lines.append(f"{rid}. [{req.get('category', 'other')}] {req['requirement']}")
        for e in evidence_map[i]:
            lines.append(f"   證據：- {e}")

    data = llm.chat_json(JUDGE_SYSTEM, JUDGE_USER.format(items="\n".join(lines)))
    if isinstance(data, dict):
        analysis = data.get("analysis", "")
        raw_judgments = data.get("judgments") or []
    elif isinstance(data, list):
        analysis = ""
        raw_judgments = data
    else:
        analysis = ""
        raw_judgments = []

    judgments = {}
    for j in raw_judgments:
        try:
            jid = int(j.get("id", -1))
        except (TypeError, ValueError):
            continue
        verdict = j.get("verdict", "partial")
        if verdict not in ("matched", "partial", "gap"):
            verdict = "partial"
        judgments[jid] = {"verdict": verdict, "reason": j.get("reason", "")}
    return judgments, analysis


def _compute_score(results: list[dict]) -> int:
    """以確定性方式算 0–100 分（不直接問 LLM 要數字，避免不可重現）。"""
    weights = {"matched": 1.0, "partial": 0.5, "gap": 0.0}
    if not results:
        return 0
    total = sum(weights[r["verdict"]] for r in results)
    return round(100 * total / len(results))
