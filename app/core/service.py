"""主业务编排。"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from app.channel.xianyu_api import XianyuApiClient
from app.channel.xianyu_client import XianyuChannelClient
from app.core.runtime_status import RuntimeStatusTracker
from app.core.settings import AppSettings
from app.core.app_types import ChatMessage, to_dict
from app.dialog.agent_core_client import AgentCoreClient
from app.dialog.service import DialogService
from app.notify.feishu import FeishuNotifier
from app.persona.service import PersonaService
from app.pricing.service import PricingService
from app.rag_engine.facade import RagEngine
from app.scheduling.service import SchedulingService
from app.store.database import BotStore


class BotApplication:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.store = BotStore(settings.paths.runtime_dir / "bot.db")
        self.status_tracker = RuntimeStatusTracker(settings.paths.runtime_dir / "runtime-status.json")
        self.pricing = PricingService(settings.paths.configs_dir / "pricing" / "default.yaml")
        self.scheduling = SchedulingService(settings.paths.configs_dir / "schedule" / "default.yaml")
        self.persona = PersonaService(settings.paths.configs_dir / "persona" / "default.yaml")
        self.agent_core_client = None
        if settings.runtime.agent_core_enabled and settings.integration.agent_core_base_url:
            self.agent_core_client = AgentCoreClient(
                base_url=settings.integration.agent_core_base_url,
                timeout_ms=settings.runtime.agent_core_timeout_ms,
                use_system_proxy=settings.runtime.use_system_proxy,
            )
        self.rag = RagEngine(
            config_path=settings.paths.configs_dir / "rag" / "default.yaml",
            cases_path=settings.paths.knowledge_dir / "cases" / "rag_cases.jsonl",
            model_settings=settings.model,
            audit_path=settings.paths.runtime_dir / "rag-audit.jsonl",
        )
        self.dialog = DialogService(
            faq_path=settings.paths.knowledge_dir / "faq" / "common.yaml",
            service_path=settings.paths.knowledge_dir / "services" / "jetson.yaml",
            handoff_path=settings.paths.configs_dir / "handoff" / "default.yaml",
            pricing_service=self.pricing,
            scheduling_service=self.scheduling,
            persona_service=self.persona,
            rag_engine=self.rag,
            agent_core_client=self.agent_core_client,
        )
        self.notifier = FeishuNotifier(
            settings.integration.feishu_webhook,
            use_system_proxy=settings.runtime.use_system_proxy,
        )
        self.status_tracker.set_boot_flags(
            cookie_loaded=bool(settings.integration.cookies_str),
            cookie_length=len(settings.integration.cookies_str),
            xianyu_enabled=settings.runtime.xianyu_enabled,
            auto_reply_enabled=settings.runtime.auto_reply_enabled,
            feishu_enabled=self.notifier.is_enabled(),
        )
        self.status_tracker.set_self_check(self._build_self_check())
        self.status_tracker.record_event("startup", "ok", "应用已完成基础初始化")
        self.channel = None
        if settings.integration.cookies_str and settings.runtime.xianyu_enabled:
            self.channel = XianyuChannelClient(
                cookies_str=settings.integration.cookies_str,
                websocket_url=settings.runtime.websocket_url,
                heartbeat_interval=settings.runtime.heartbeat_interval,
                heartbeat_timeout=settings.runtime.heartbeat_timeout,
                message_expire_ms=settings.runtime.message_expire_ms,
                use_system_proxy=settings.runtime.use_system_proxy,
                user_agent=settings.runtime.xianyu_user_agent,
                simulate_human_typing=settings.runtime.simulate_human_typing,
                status_callback=self._record_channel_status,
                diagnostics_dir=settings.paths.exports_dir / "xianyu-diagnostics",
            )

    async def run(self) -> None:
        if not self.channel:
            self.logger.warning("未配置闲鱼 Cookie 或已关闭闲鱼接入，当前只启动本地后台。")
            self.status_tracker.record_event("startup", "warning", "闲鱼接入未启用，当前只启动本地后台")
            while True:
                await asyncio.sleep(3600)
        await self.channel.connect_and_listen(self.handle_incoming_message)

    async def handle_incoming_message(self, message: ChatMessage) -> None:
        self.status_tracker.mark_message_received(
            summary=f"{message.sender_name}: {message.content[:80]}"
        )
        self.status_tracker.record_event(
            "message_dispatch",
            "ok",
            "消息已进入业务处理",
            chat_id=message.chat_id,
            sender_name=message.sender_name,
            is_self=message.is_self,
        )
        role = "assistant" if message.is_self else "user"
        self.store.save_message(
            chat_id=message.chat_id,
            item_id=message.item_id or "unknown",
            sender_id=message.sender_id,
            sender_name=message.sender_name,
            role=role,
            content=message.content,
            created_at_ms=message.created_at_ms,
        )

        if message.is_self:
            self.status_tracker.record_event(
                "manual_mode",
                "ok",
                "检测到你本人已回复，会话切换为人工接管",
                chat_id=message.chat_id,
            )
            self.store.touch_conversation_status(
                chat_id=message.chat_id,
                status="manual",
                last_message=message.content,
            )
            return

        if self.store.is_manual_mode(message.chat_id):
            self.status_tracker.record_event(
                "manual_mode",
                "skip",
                "当前会话处于人工接管，机器人跳过自动回复",
                chat_id=message.chat_id,
            )
            self.store.upsert_conversation(
                chat_id=message.chat_id,
                item_id=message.item_id or "unknown",
                customer_id=message.sender_id,
                customer_name=message.sender_name,
                status="manual",
                manual_mode=True,
                last_message=message.content,
            )
            return

        item_title = "Jetson 服务"
        cached_item = self.store.get_item(message.item_id) if message.item_id else None
        if cached_item:
            item_title = cached_item.get("title") or item_title

        history = self.store.get_chat_history(message.chat_id, limit=None)
        decision = self.dialog.decide(
            message.content,
            item_title=item_title,
            chat_id=message.chat_id,
            item_id=message.item_id or "",
            conversation_history=history,
            meta={"sender_name": message.sender_name},
        )
        self.status_tracker.record_event(
            "decision",
            "ok",
            f"已完成对话决策: {decision.action}",
            chat_id=message.chat_id,
            reasons=decision.reasons,
        )
        status = "handoff" if decision.handoff_required else decision.action

        self.store.upsert_conversation(
            chat_id=message.chat_id,
            item_id=message.item_id or "unknown",
            customer_id=message.sender_id,
            customer_name=message.sender_name,
            status=status,
            manual_mode=decision.handoff_required,
            last_message=message.content,
        )

        if decision.schedule and decision.schedule.suggestions:
            self.store.create_appointment(
                chat_id=message.chat_id,
                item_id=message.item_id or "unknown",
                customer_name=message.sender_name,
                slot_text=" | ".join(decision.schedule.suggestions),
            )

        if decision.handoff_required:
            reason = "；".join(decision.reasons) if decision.reasons else "触发人工接管"
            self.store.create_escalation(
                chat_id=message.chat_id,
                item_id=message.item_id or "unknown",
                customer_name=message.sender_name,
                reason=reason,
                summary=decision.handoff_summary or decision.reply_text,
            )
            self.notifier.send_text(
                "闲鱼机器人转人工提醒",
                [
                    f"客户：{message.sender_name}",
                    f"会话：{message.chat_id}",
                    f"商品：{message.item_id or 'unknown'}",
                    f"问题：{message.content}",
                    f"原因：{reason}",
                    "状态：该会话已切换为人工接管，机器人已静默。",
                ],
            )
            self.status_tracker.record_event(
                "handoff",
                "ok",
                "已触发人工接管并发送提醒",
                chat_id=message.chat_id,
                reason=reason,
            )

        if self.channel and self.settings.runtime.auto_reply_enabled:
            await self.channel.send_text(message.chat_id, message.sender_id, decision.reply_text)
            self.store.save_message(
                chat_id=message.chat_id,
                item_id=message.item_id or "unknown",
                sender_id="bot",
                sender_name="bot",
                role="assistant",
                content=decision.reply_text,
                created_at_ms=message.created_at_ms + 1,
            )
            self.status_tracker.record_event(
                "reply_send",
                "ok",
                "自动回复已写入记录并发送",
                chat_id=message.chat_id,
                preview=decision.reply_text[:80],
            )

    def get_conversations(self) -> list[dict]:
        return [to_dict(item) for item in self.store.list_conversations()]

    def get_escalations(self) -> list[dict]:
        return self.store.list_escalations()

    def get_appointments(self) -> list[dict]:
        return self.store.list_appointments()

    def set_manual_mode(self, chat_id: str, manual_mode: bool) -> None:
        self.store.set_manual_mode(chat_id, manual_mode)
        self.status_tracker.record_event(
            "manual_mode",
            "ok",
            "后台已手动切换会话接管状态",
            chat_id=chat_id,
            manual_mode=manual_mode,
        )

    def get_runtime_status(self) -> dict:
        return self.status_tracker.snapshot()

    def simulate_local_message(
        self,
        *,
        message_text: str,
        chat_id: str = "debug-chat",
        sender_id: str = "debug-user",
        sender_name: str = "本地测试客户",
        item_id: str = "debug-item",
        notify: bool = False,
    ) -> dict:
        """本地调试入口：不依赖闲鱼通道，直接验证回复/转人工/预约流程。"""
        now_ms = int(time.time() * 1000)
        message = ChatMessage(
            chat_id=chat_id,
            item_id=item_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=message_text,
            created_at_ms=now_ms,
            is_self=False,
        )
        self.status_tracker.record_event(
            "debug",
            "ok",
            "收到本地模拟消息",
            chat_id=chat_id,
            sender_name=sender_name,
        )
        self.store.save_message(
            chat_id=message.chat_id,
            item_id=message.item_id,
            sender_id=message.sender_id,
            sender_name=message.sender_name,
            role="user",
            content=message.content,
            created_at_ms=message.created_at_ms,
        )
        if self.store.is_manual_mode(message.chat_id):
            self.store.upsert_conversation(
                chat_id=message.chat_id,
                item_id=message.item_id,
                customer_id=message.sender_id,
                customer_name=message.sender_name,
                status="manual",
                manual_mode=True,
                last_message=message.content,
            )
            return {"action": "manual", "reply_text": "当前会话为人工接管，模拟消息未触发自动回复。"}

        item_title = "Jetson 服务"
        cached_item = self.store.get_item(message.item_id) if message.item_id else None
        if cached_item:
            item_title = cached_item.get("title") or item_title
        history = self.store.get_chat_history(message.chat_id, limit=None)
        decision = self.dialog.decide(
            message.content,
            item_title=item_title,
            chat_id=message.chat_id,
            item_id=message.item_id,
            conversation_history=history,
            meta={"sender_name": message.sender_name, "simulate": True},
        )
        status = "handoff" if decision.handoff_required else decision.action
        self.store.upsert_conversation(
            chat_id=message.chat_id,
            item_id=message.item_id,
            customer_id=message.sender_id,
            customer_name=message.sender_name,
            status=status,
            manual_mode=decision.handoff_required,
            last_message=message.content,
        )
        if decision.schedule and decision.schedule.suggestions:
            self.store.create_appointment(
                chat_id=message.chat_id,
                item_id=message.item_id,
                customer_name=message.sender_name,
                slot_text=" | ".join(decision.schedule.suggestions),
            )
        if decision.handoff_required:
            reason = "，".join(decision.reasons) if decision.reasons else "触发人工接管"
            self.store.create_escalation(
                chat_id=message.chat_id,
                item_id=message.item_id,
                customer_name=message.sender_name,
                reason=reason,
                summary=decision.handoff_summary or decision.reply_text,
            )
            notify_sent = False
            if notify:
                notify_sent = self.notifier.send_text(
                    "闲鱼机器人本地测试-人工接管提醒",
                    [
                        f"客户：{message.sender_name}",
                        f"会话：{message.chat_id}",
                        f"问题：{message.content}",
                        f"原因：{reason}",
                    ],
                )
        else:
            notify_sent = False
        self.store.save_message(
            chat_id=message.chat_id,
            item_id=message.item_id,
            sender_id="bot",
            sender_name="bot",
            role="assistant",
            content=decision.reply_text,
            created_at_ms=message.created_at_ms + 1,
        )
        return {
            "action": decision.action,
            "handoff_required": decision.handoff_required,
            "reply_text": decision.reply_text,
            "reasons": decision.reasons,
            "schedule_suggestions": decision.schedule.suggestions if decision.schedule else [],
            "quote_price": decision.quote.price if decision.quote else None,
            "notify_attempted": bool(notify and decision.handoff_required),
            "notify_sent": notify_sent,
        }

    def _record_channel_status(self, stage: str, status: str, detail: str, **extra: object) -> None:
        self.status_tracker.record_event(stage, status, detail, **extra)
        if stage == "token":
            self.status_tracker.set_token_status(status == "ok", detail)
        elif stage == "message_receive" and status == "ok":
            payload_len = extra.get("payload_length")
            summary = f"{detail} (payload_length={payload_len})" if payload_len else detail
            self.status_tracker.mark_message_received(summary)
        elif stage == "websocket":
            self.status_tracker.set_websocket_status(status, detail)
            if status == "error":
                self.status_tracker.mark_error(detail)
        elif status == "error":
            self.status_tracker.mark_error(detail)
        elif status == "skip":
            self.status_tracker.mark_skip(detail)

    def _build_self_check(self) -> dict:
        root = self.settings.paths.root
        required_paths = [
            root / ".env",
            self.settings.paths.configs_dir / "pricing" / "default.yaml",
            self.settings.paths.configs_dir / "schedule" / "default.yaml",
            self.settings.paths.configs_dir / "handoff" / "default.yaml",
            self.settings.paths.configs_dir / "rag" / "default.yaml",
            self.settings.paths.knowledge_dir / "faq" / "common.yaml",
            self.settings.paths.knowledge_dir / "services" / "jetson.yaml",
            self.settings.paths.knowledge_dir / "cases" / "rag_cases.jsonl",
        ]
        diagnostics_path = self.settings.paths.runtime_dir / "self-check.txt"
        diagnostics_path.write_text("ok", encoding="utf-8")
        cookie_health = XianyuApiClient(
            self.settings.integration.cookies_str,
            use_system_proxy=self.settings.runtime.use_system_proxy,
            user_agent=self.settings.runtime.xianyu_user_agent,
        ).get_cookie_health()
        return {
            "env_loaded": (root / ".env").exists(),
            "cookie_loaded": bool(self.settings.integration.cookies_str),
            "cookie_length": len(self.settings.integration.cookies_str),
            "cookie_health": cookie_health,
            "use_system_proxy": self.settings.runtime.use_system_proxy,
            "feishu_enabled": self.notifier.is_enabled(),
            "xianyu_enabled": self.settings.runtime.xianyu_enabled,
            "auto_reply_enabled": self.settings.runtime.auto_reply_enabled,
            "agent_core_enabled": self.settings.runtime.agent_core_enabled,
            "agent_core_base_url": self.settings.integration.agent_core_base_url,
            "config_files": [
                {"path": str(path), "exists": path.exists()} for path in required_paths
            ],
            "database_path": str(self.store.db_path),
            "database_path_exists": Path(self.store.db_path).exists(),
            "runtime_dir_writable": diagnostics_path.exists(),
        }
