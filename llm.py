"""DeepSeek（OpenAI 相容）客戶端。"""
from __future__ import annotations

import json

from openai import OpenAI

import config

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
    return _client


def chat_json(system: str, user: str, temperature: float = 0.0) -> dict:
    """呼叫 LLM，回傳解析後的 JSON dict。

    - thinking=disabled：deepseek-flash 是推理型模型，關掉思考後快約 3 倍、也更省 token。
    - 不用 response_format=json_object（有額外延遲），改由 _parse_json 手動抽取 JSON。
    """
    resp = get_client().chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        extra_body={"thinking": {"type": "disabled"}},
    )
    return _parse_json(resp.choices[0].message.content)


def _parse_json(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 若模型偶爾在 JSON 外多輸出文字，抓第一個 { ... }
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise
