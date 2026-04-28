"""Small in-memory TTL cache."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _Entry:
    value: Any
    expire_at: float


class TTLCache:
    def __init__(self, ttl_seconds: float = 120.0, max_items: int = 512) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self._data: dict[str, _Entry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if not entry:
            return None
        if entry.expire_at < time.time():
            self._data.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        if len(self._data) >= self.max_items:
            oldest_key = next(iter(self._data.keys()))
            self._data.pop(oldest_key, None)
        self._data[key] = _Entry(value=value, expire_at=time.time() + self.ttl_seconds)
