"""运行时状态与诊断信息。"""

from __future__ import annotations

import json
from collections import deque
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RuntimeStatusTracker:
    def __init__(self, status_path: Path, max_events: int = 30) -> None:
        self.status_path = status_path
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_events = max_events
        self._lock = Lock()
        self._state: dict[str, Any] = {
            "connection": {
                "cookie_loaded": False,
                "cookie_length": 0,
                "xianyu_enabled": False,
                "auto_reply_enabled": False,
                "feishu_enabled": False,
                "token_status": "unknown",
                "websocket_status": "unknown",
                "last_message_at": "",
                "last_error": "",
                "last_error_at": "",
                "disconnect_count": 0,
                "last_raw_message_summary": "",
                "last_skip_reason": "",
            },
            "self_check": {},
            "events": [],
        }
        self._events = deque(maxlen=max_events)
        self._save()

    def set_boot_flags(
        self,
        *,
        cookie_loaded: bool,
        cookie_length: int,
        xianyu_enabled: bool,
        auto_reply_enabled: bool,
        feishu_enabled: bool,
    ) -> None:
        with self._lock:
            conn = self._state["connection"]
            conn["cookie_loaded"] = cookie_loaded
            conn["cookie_length"] = cookie_length
            conn["xianyu_enabled"] = xianyu_enabled
            conn["auto_reply_enabled"] = auto_reply_enabled
            conn["feishu_enabled"] = feishu_enabled
            self._save()

    def set_self_check(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._state["self_check"] = payload
            self._save()

    def record_event(self, stage: str, status: str, detail: str, **extra: Any) -> None:
        event = {
            "time": now_text(),
            "stage": stage,
            "status": status,
            "detail": detail,
        }
        event.update(extra)
        with self._lock:
            self._events.appendleft(event)
            self._state["events"] = list(self._events)
            self._save()

    def set_token_status(self, ok: bool, detail: str) -> None:
        with self._lock:
            self._state["connection"]["token_status"] = "ok" if ok else "failed"
            if not ok:
                self._state["connection"]["last_error"] = detail
                self._state["connection"]["last_error_at"] = now_text()
            self._save()

    def set_websocket_status(self, status: str, detail: str = "") -> None:
        with self._lock:
            self._state["connection"]["websocket_status"] = status
            if detail:
                self._state["connection"]["last_skip_reason"] = detail
            self._save()

    def mark_message_received(self, summary: str) -> None:
        with self._lock:
            self._state["connection"]["last_message_at"] = now_text()
            self._state["connection"]["last_raw_message_summary"] = summary
            self._save()

    def mark_skip(self, reason: str) -> None:
        with self._lock:
            self._state["connection"]["last_skip_reason"] = reason
            self._save()

    def mark_error(self, error_text: str) -> None:
        with self._lock:
            conn = self._state["connection"]
            conn["last_error"] = error_text
            conn["last_error_at"] = now_text()
            conn["disconnect_count"] += 1
            self._save()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._state, ensure_ascii=False))

    def _save(self) -> None:
        self.status_path.write_text(
            json.dumps(self._state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
