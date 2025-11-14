from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_MODEL = "gpt-4o"
ASSISTANT_URL = "https://api.openai.com/v1/chat/completions"


class AssistantError(Exception):
    """Indicates the assistant API request failed."""


def call_assistant(
    api_key: str,
    messages: List[Dict[str, Any]],
    max_tokens: int = 512,
    temperature: float = 0.7,
    model: str | None = None,
) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    body = json.dumps(payload).encode("utf-8")
    request = Request(ASSISTANT_URL, data=body, headers=headers, method="POST")

    try:
        with urlopen(request, timeout=30) as response:
            response_data = response.read()
    except (HTTPError, URLError) as exc:
        raise AssistantError(f"Assistant request failed: {exc}") from exc

    data = json.loads(response_data.decode("utf-8"))
    choice = data.get("choices", [{}])[0]
    return choice.get("message", {}).get("content", "")
