"""聯網搜尋（DuckDuckGo，免費、免 API key）。"""
from __future__ import annotations

from ddgs import DDGS


def search(query: str, max_results: int = 4) -> list[dict]:
    """回傳 [{title, url, snippet}]；失敗或無結果時回傳空清單（fail-safe）。"""
    if not query or not query.strip():
        return []
    try:
        results = DDGS().text(query, max_results=max_results)
    except Exception:  # noqa: BLE001
        return []

    out = []
    for r in results or []:
        out.append({
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": (r.get("body") or r.get("snippet") or "")[:300],
        })
    return out
