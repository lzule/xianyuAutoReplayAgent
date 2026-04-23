"""飞书提醒。"""

from __future__ import annotations

import json
import logging
from urllib import request


class FeishuNotifier:
    def __init__(self, webhook_url: str, use_system_proxy: bool = False) -> None:
        self.webhook_url = webhook_url.strip()
        self.use_system_proxy = use_system_proxy
        self.logger = logging.getLogger(__name__)
        handlers: list[request.BaseHandler] = []
        if not use_system_proxy:
            handlers.append(request.ProxyHandler({}))
        self.opener = request.build_opener(*handlers)

    def is_enabled(self) -> bool:
        return bool(self.webhook_url)

    def send_text(self, title: str, lines: list[str]) -> bool:
        if not self.is_enabled():
            self.logger.info("未配置飞书 webhook，跳过提醒。")
            return False

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": title}},
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}}
                ],
            },
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener.open(req, timeout=10) as resp:
                ok = 200 <= resp.status < 300
                if not ok:
                    self.logger.warning("飞书提醒失败，状态码: %s", resp.status)
                return ok
        except Exception as exc:
            self.logger.warning("飞书提醒失败: %s", exc)
            return False
