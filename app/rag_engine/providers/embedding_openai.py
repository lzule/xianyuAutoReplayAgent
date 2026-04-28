"""OpenAI-compatible embeddings provider."""

from __future__ import annotations

import json
from urllib import request


class OpenAIEmbeddingProvider:
    def __init__(self, api_key: str, base_url: str, model_name: str) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name.strip()

    def is_ready(self) -> bool:
        return bool(self.api_key and self.base_url and self.model_name)

    def embed_texts(self, texts: list[str], timeout_seconds: float = 4.0) -> list[list[float]]:
        if not self.is_ready() or not texts:
            return []
        payload = {
            "model": self.model_name,
            "input": texts,
        }
        req = request.Request(
            f"{self.base_url}/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
        data = parsed.get("data", [])
        vectors: list[list[float]] = []
        for item in data:
            vector = item.get("embedding", [])
            if isinstance(vector, list):
                vectors.append([float(v) for v in vector])
        return vectors
