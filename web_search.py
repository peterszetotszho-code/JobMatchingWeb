"""Web search via DuckDuckGo (free, no API key, HK-oriented)."""
from __future__ import annotations

from ddgs import DDGS


def search(query: str, max_results: int = 4) -> list[dict]:
    """Return [{title, url, snippet}]; returns [] on failure (fail-safe)."""
    if not query or not query.strip():
        return []
    # HK-oriented: avoid Taiwan/other-region results
    q = query.strip()
    if "香港" not in q and "Hong Kong" not in q:
        q = f"{q} 香港"

    try:
        results = DDGS().text(q, max_results=max_results)
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
