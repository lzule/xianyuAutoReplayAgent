"""HTTP client for external agent core service."""

from __future__ import annotations

import json
import logging
import ssl
from typing import Any
from urllib import request


class AgentCoreClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_ms: int = 6000,
        use_system_proxy: bool = False,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = max(1.0, timeout_ms / 1000.0)
        handlers: list[request.BaseHandler] = []
        if not use_system_proxy:
            handlers.append(request.ProxyHandler({}))
        handlers.append(request.HTTPSHandler(context=ssl.create_default_context()))
        self.opener = request.build_opener(*handlers)

    def enabled(self) -> bool:
        return bool(self.base_url)

    def reply(
        self,
        *,
        chat_id: str,
        item_id: str,
        customer_text: str,
        conversation_history: list[dict[str, Any]],
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not self.enabled():
            return None
        payload = {
            "chat_id": chat_id,
            "item_id": item_id,
            "customer_text": customer_text,
            "conversation_history": conversation_history,
            "meta": meta or {},
        }
        req = request.Request(
            f"{self.base_url}/v1/reply",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener.open(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            self.logger.warning("调用外部 agent_core 失败，回退本地决策: %s", exc)
            return None
