"""LLM client (OpenAI-compatible)."""
from __future__ import annotations

import json

from openai import OpenAI

import config

_client: OpenAI | None = None

# the model is a reasoning model; disabling thinking makes it ~3x faster and cheaper
_THINKING = {"thinking": {"type": "disabled"}}


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
    return _client


def _messages(system: str, user: str) -> list[dict]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def chat(system: str, user: str, temperature: float = 0.0) -> str:
    """Call the LLM and return plain text."""
    resp = get_client().chat.completions.create(
        model=config.LLM_MODEL,
        messages=_messages(system, user),
        temperature=temperature,
        extra_body=_THINKING,
    )
    return resp.choices[0].message.content or ""


def chat_stream(system: str, user: str, temperature: float = 0.0):
    """Streaming variant: yields text chunks."""
    resp = get_client().chat.completions.create(
        model=config.LLM_MODEL,
        messages=_messages(system, user),
        temperature=temperature,
        stream=True,
        extra_body=_THINKING,
    )
    for chunk in resp:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def chat_json(system: str, user: str, temperature: float = 0.0):
    """Call the LLM and return parsed JSON (dict or list).

    Deliberately avoids response_format=json_object (extra latency); parses manually instead.
    """
    return _parse_json(chat(system, user, temperature))


def _parse_json(content: str):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # if the model wraps JSON in extra text, extract the first { ... } block
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise
