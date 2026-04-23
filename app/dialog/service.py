"""对话决策引擎。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.app_types import Decision
from app.persona.service import PersonaService
from app.pricing.service import PricingService
from app.scheduling.service import SchedulingService


class DialogService:
    def __init__(
        self,
        faq_path: Path,
        service_path: Path,
        handoff_path: Path,
        pricing_service: PricingService,
        scheduling_service: SchedulingService,
        persona_service: PersonaService,
    ) -> None:
        self.faq_path = faq_path
        self.service_path = service_path
        self.handoff_path = handoff_path
        self.pricing_service = pricing_service
        self.scheduling_service = scheduling_service
        self.persona_service = persona_service
        self.reload()

    def reload(self) -> None:
        self.faq_data = yaml.safe_load(self.faq_path.read_text(encoding="utf-8")) or {}
        self.service_data = yaml.safe_load(self.service_path.read_text(encoding="utf-8")) or {}
        self.handoff_data = yaml.safe_load(self.handoff_path.read_text(encoding="utf-8")) or {}
        self.pricing_service.reload()
        self.scheduling_service.reload()
        self.persona_service.reload()

    def decide(self, message_text: str, item_title: str) -> Decision:
        text = message_text.strip()
        lowered = text.lower()

        if self._must_handoff(lowered):
            summary = "当前问题需要负责人确认，我先帮您联系一下，稍后由负责人直接回复您。"
            return Decision(
                action="handoff",
                reply_text=self.persona_service.polish(summary),
                handoff_required=True,
                handoff_summary=summary,
                reasons=["命中人工接管规则"],
            )

        faq_reply = self._match_faq(lowered)
        if faq_reply:
            return Decision(
                action="reply",
                reply_text=self.persona_service.polish(faq_reply),
                reasons=["命中常见问题"],
            )

        if any(keyword in lowered for keyword in ["价格", "报价", "多少钱", "怎么收费", "便宜", "优惠", "费用"]):
            quote = self.pricing_service.quote(item_title=item_title, message_text=text)
            if quote.needs_handoff:
                return Decision(
                    action="handoff",
                    reply_text=self.persona_service.polish(quote.summary),
                    quote=quote,
                    handoff_required=True,
                    handoff_summary=quote.summary,
                    reasons=quote.reasons,
                )
            return Decision(
                action="quote",
                reply_text=self.persona_service.polish(quote.summary),
                quote=quote,
                reasons=quote.reasons or ["自动报价"],
            )

        if any(keyword in lowered for keyword in ["什么时候", "时间", "几点", "预约", "安排", "有空"]):
            schedule = self.scheduling_service.suggest_slots(text)
            if schedule.needs_handoff:
                return Decision(
                    action="handoff",
                    reply_text=self.persona_service.polish(schedule.summary),
                    schedule=schedule,
                    handoff_required=True,
                    handoff_summary=schedule.summary,
                    reasons=["缺少可预约时间"],
                )
            return Decision(
                action="schedule",
                reply_text=self.persona_service.polish(schedule.summary),
                schedule=schedule,
                reasons=["自动推荐预约时间"],
            )

        default_reply = self._build_default_reply()
        return Decision(
            action="reply",
            reply_text=self.persona_service.polish(default_reply),
            reasons=["默认回复"],
        )

    def _match_faq(self, lowered_text: str) -> str:
        for item in self.faq_data.get("items", []):
            keywords = [keyword.lower() for keyword in item.get("keywords", [])]
            if any(keyword in lowered_text for keyword in keywords):
                return item.get("reply", "")
        return ""

    def _must_handoff(self, lowered_text: str) -> bool:
        for keyword in self.handoff_data.get("handoff_keywords", []):
            if keyword.lower() in lowered_text:
                return True
        return False

    def _build_default_reply(self) -> str:
        intro = self.service_data.get("default_intro", "我这边先帮您看一下需求。")
        ask = self.service_data.get(
            "default_followup",
            "您可以把当前板卡型号、环境情况、想实现的目标和时间要求发我，我先帮您判断能不能接。",
        )
        return f"{intro}{ask}"
