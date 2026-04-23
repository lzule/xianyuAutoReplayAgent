"""报价规则。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.app_types import QuoteResult


class PricingService:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.data = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        return yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}

    def reload(self) -> None:
        self.data = self._load_config()

    def get_default_service(self) -> tuple[str, dict[str, Any]]:
        services = self.data.get("services", {})
        if not services:
            return "unknown", {}
        key = next(iter(services))
        return key, services[key]

    def match_service(self, item_title: str, message_text: str) -> tuple[str, dict[str, Any]]:
        combined = f"{item_title} {message_text}".lower()
        for key, service in self.data.get("services", {}).items():
            aliases = [key.lower(), *[alias.lower() for alias in service.get("aliases", [])]]
            if any(alias in combined for alias in aliases):
                return key, service
        return self.get_default_service()

    def quote(self, item_title: str, message_text: str) -> QuoteResult:
        service_key, service = self.match_service(item_title, message_text)
        base_price = int(service.get("base_price", 0))
        minimum_price = int(service.get("minimum_price", base_price))
        urgent_multiplier = float(service.get("urgent_multiplier", 1.0))
        handoff_keywords = service.get("handoff_keywords", [])

        reasons: list[str] = []
        needs_handoff = False
        price = base_price
        normalized = message_text.lower()

        if any(keyword.lower() in normalized for keyword in handoff_keywords):
            needs_handoff = True
            reasons.append("需求触发了人工报价边界")

        if any(word in normalized for word in ["加急", "今天", "今晚", "马上", "立刻", "紧急"]):
            price = int(round(base_price * urgent_multiplier))
            reasons.append("包含加急需求")

        if any(word in normalized for word in ["便宜", "优惠", "少点", "最低", "砍价"]):
            reasons.append("客户正在议价")
            price = max(minimum_price, price)

        summary = f"这项服务当前可按 {price} 元先评估安排，具体边界我会按需求细节再确认。"
        if needs_handoff:
            summary = "这个需求超出自动报价边界，需要我先联系负责人确认价格后再回复您。"

        return QuoteResult(
            service_key=service_key,
            price=price,
            summary=summary,
            needs_handoff=needs_handoff,
            reasons=reasons,
        )
