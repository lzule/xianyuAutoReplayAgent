"""OpenAI-compatible chat completion provider."""

from __future__ import annotations

import json
from urllib import request


class OpenAILLMProvider:
    def __init__(self, api_key: str, base_url: str, model_name: str) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name.strip()

    def is_ready(self) -> bool:
        return bool(self.api_key and self.base_url and self.model_name)

    def generate(self, system_prompt: str, user_prompt: str, timeout_seconds: float = 6.0) -> str:
        if not self.is_ready():
            return ""
        payload = {
            "model": self.model_name,
            "temperature": 0.5,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
        choices = parsed.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return str(message.get("content") or "").strip()
