"""Audit logger for rag pipeline."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, target: Path, enabled: bool = True) -> None:
        self.target = target
        self.enabled = enabled
        self.target.parent.mkdir(parents=True, exist_ok=True)

    def log(self, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        item = {
            "ts": int(time.time() * 1000),
            **payload,
        }
        with self.target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
