"""临时口吻生成。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class PersonaService:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        return yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}

    def reload(self) -> None:
        self.data = self._load()

    def polish(self, text: str) -> str:
        prefix = self.data.get("reply_prefix", "")
        suffix = self.data.get("reply_suffix", "")
        result = f"{prefix}{text}{suffix}".strip()
        return result
