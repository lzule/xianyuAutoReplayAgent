"""RAG settings loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RagSettings:
    enabled: bool = False
    gray_ratio: float = 0.0
    recall_k: int = 30
    rerank_k: int = 10
    min_score: float = 0.25
    soft_timeout_ms: int = 2000
    hard_timeout_ms: int = 6000
    max_cases_in_prompt: int = 8
    audit_enabled: bool = True


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return default


def load_rag_settings(path: Path) -> RagSettings:
    if not path.exists():
        return RagSettings()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        return RagSettings(
            enabled=_as_bool(data.get("enabled"), False),
            gray_ratio=max(0.0, min(1.0, float(data.get("gray_ratio", 0.0)))),
            recall_k=max(5, int(data.get("recall_k", 30))),
            rerank_k=max(3, int(data.get("rerank_k", 10))),
            min_score=max(0.0, min(1.0, float(data.get("min_score", 0.25)))),
            soft_timeout_ms=max(200, int(data.get("soft_timeout_ms", 2000))),
            hard_timeout_ms=max(1000, int(data.get("hard_timeout_ms", 6000))),
            max_cases_in_prompt=max(1, int(data.get("max_cases_in_prompt", 8))),
            audit_enabled=_as_bool(data.get("audit_enabled"), True),
        )
    except (TypeError, ValueError):
        return RagSettings()
