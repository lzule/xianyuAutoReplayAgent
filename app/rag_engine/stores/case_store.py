"""RAG case loader."""

from __future__ import annotations

import json
from pathlib import Path

from app.rag_engine.types import Case


class CaseStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.cases: list[Case] = []
        self.reload()

    def reload(self) -> None:
        self.cases = []
        if not self.path.exists():
            return
        for idx, raw_line in enumerate(self.path.read_text(encoding="utf-8").splitlines()):
            line = raw_line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            case_id = str(item.get("case_id") or f"case-{idx}")
            user_query = str(item.get("user_query") or "").strip()
            agent_reply = str(item.get("agent_reply") or "").strip()
            if not user_query or not agent_reply:
                continue
            style_tags_raw = item.get("style_tags", [])
            style_tags = [str(tag) for tag in style_tags_raw] if isinstance(style_tags_raw, list) else []
            self.cases.append(
                Case(
                    case_id=case_id,
                    intent=str(item.get("intent") or "general"),
                    product_hint=str(item.get("product_hint") or ""),
                    user_query=user_query,
                    agent_reply=agent_reply,
                    outcome_tag=str(item.get("outcome_tag") or "unknown"),
                    style_tags=style_tags,
                    created_at=str(item.get("created_at") or ""),
                )
            )
