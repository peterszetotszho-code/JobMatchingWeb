"""DeepSeek（OpenAI 相容）客戶端。"""
from __future__ import annotations

import json

from openai import OpenAI

import config

_client: OpenAI | None = None

# deepseek-flash 是推理型模型，關掉思考後快約 3 倍、也更省 token
_THINKING = {"thinking": {"type": "disabled"}}


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
    return _client


def _messages(system: str, user: str) -> list[dict]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def chat(system: str, user: str, temperature: float = 0.0) -> str:
    """呼叫 LLM，回傳純文字內容。"""
    resp = get_client().chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=_messages(system, user),
        temperature=temperature,
        extra_body=_THINKING,
    )
    return resp.choices[0].message.content or ""


def chat_stream(system: str, user: str, temperature: float = 0.0):
    """串流版：yield 文字片段。"""
    resp = get_client().chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=_messages(system, user),
        temperature=temperature,
        stream=True,
        extra_body=_THINKING,
    )
    for chunk in resp:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def chat_json(system: str, user: str, temperature: float = 0.0):
    """呼叫 LLM，回傳解析後的 JSON（dict 或 list）。

    刻意不用 response_format=json_object（有額外延遲），改由 _parse_json 手動抽取。
    """
    return _parse_json(chat(system, user, temperature))


def _parse_json(content: str):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 若模型偶爾在 JSON 外多輸出文字，抓第一個 { ... }
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise
