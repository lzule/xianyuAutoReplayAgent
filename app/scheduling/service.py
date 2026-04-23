"""预约规则。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.app_types import ScheduleResult


class SchedulingService:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        return yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}

    def reload(self) -> None:
        self.data = self._load()

    def suggest_slots(self, message_text: str) -> ScheduleResult:
        weekly = self.data.get("weekly_slots", {})
        suggestions: list[str] = []

        for day, slots in weekly.items():
            for slot in slots[:2]:
                suggestions.append(f"{day} {slot}")
            if len(suggestions) >= 4:
                break

        if not suggestions:
            return ScheduleResult(
                matched=False,
                summary="我这边还没配置可预约时间，先联系负责人确认后再给您具体安排。",
                needs_handoff=True,
            )

        return ScheduleResult(
            matched=True,
            summary=f"我这边先给您几个可安排时间：{'；'.join(suggestions)}，您看哪个方便。",
            suggestions=suggestions,
        )
