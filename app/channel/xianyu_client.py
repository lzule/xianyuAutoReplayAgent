"""闲鱼消息通道客户端。"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import websockets

from app.channel.xianyu_api import XianyuApiClient
from app.channel.xianyu_utils import (
    cookies_to_header,
    decrypt_message,
    generate_device_id,
    generate_mid,
    generate_uuid,
    parse_cookies,
    to_text_payload,
)
from app.core.app_types import ChatMessage


MessageHandler = Callable[[ChatMessage], Awaitable[None]]


class XianyuChannelClient:
    def __init__(
        self,
        cookies_str: str,
        websocket_url: str,
        heartbeat_interval: int,
        heartbeat_timeout: int,
        message_expire_ms: int,
        use_system_proxy: bool = False,
        user_agent: str = "Mozilla/5.0",
        simulate_human_typing: bool = False,
        status_callback: Callable[..., None] | None = None,
        diagnostics_dir: Path | None = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.cookies_str = cookies_str
        self.cookies = parse_cookies(cookies_str)
        self.cookie_header = cookies_to_header(self.cookies)
        self.websocket_url = websocket_url
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.message_expire_ms = message_expire_ms
        self.use_system_proxy = use_system_proxy
        self.user_agent = user_agent
        self.simulate_human_typing = simulate_human_typing
        self.api = XianyuApiClient(
            cookies_str,
            use_system_proxy=use_system_proxy,
            user_agent=user_agent,
        )
        self.my_id = self.cookies.get("unb", "")
        self.device_id = generate_device_id(self.my_id or "unknown")
        self.current_token = ""
        self.last_heartbeat = 0.0
        self.last_heartbeat_response = 0.0
        self.ws: websockets.WebSocketClientProtocol | None = None
        self.status_callback = status_callback
        self.diagnostics_dir = diagnostics_dir
        if self.diagnostics_dir is not None:
            self.diagnostics_dir.mkdir(parents=True, exist_ok=True)

    async def connect_and_listen(self, handler: MessageHandler) -> None:
        while True:
            try:
                self._status("connect", "starting", "开始建立闲鱼连接")
                await self._connect_once(handler)
            except Exception as exc:
                self.logger.warning("闲鱼连接中断: %s", exc)
                self._status("connect", "error", f"闲鱼连接中断: {exc}")
                await asyncio.sleep(5)

    async def send_text(self, chat_id: str, to_user_id: str, text: str) -> None:
        if not self.ws:
            raise RuntimeError("闲鱼连接尚未建立")
        if self.simulate_human_typing:
            await asyncio.sleep(min(10.0, random.uniform(0.1, 0.3) * len(text)))

        msg = {
            "lwp": "/r/MessageSend/sendByReceiverScope",
            "headers": {"mid": generate_mid()},
            "body": [
                {
                    "uuid": generate_uuid(),
                    "cid": f"{chat_id}@goofish",
                    "conversationType": 1,
                    "content": {
                        "contentType": 101,
                        "custom": {"type": 1, "data": to_text_payload(text)},
                    },
                    "extension": {"extJson": "{}"},
                    "ctx": {"appVersion": "1.0", "platform": "web"},
                    "mtags": {},
                    "msgReadStatusSetting": 1,
                    "redPointPolicy": 0,
                },
                {"actualReceivers": [f"{to_user_id}@goofish", f"{self.my_id}@goofish"]},
            ],
        }
        await self.ws.send(json.dumps(msg, ensure_ascii=False))
        self._status("reply_send", "ok", "自动回复已发送", chat_id=chat_id, to_user_id=to_user_id)

    async def _connect_once(self, handler: MessageHandler) -> None:
        self._status("token", "starting", "开始获取闲鱼 token")
        token_response = self.api.get_token(self.device_id)
        self.current_token = token_response.get("data", {}).get("accessToken", "")
        if not self.current_token:
            self._status("token", "error", "未能获取闲鱼 token", token_response=token_response)
            raise RuntimeError(f"未能获取闲鱼 token: {token_response}")
        self._status("token", "ok", "已获取闲鱼 token")

        headers = {
            "Cookie": self.cookie_header,
            "Host": "wss-goofish.dingtalk.com",
            "Connection": "Upgrade",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Origin": "https://www.goofish.com",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": self.user_agent,
        }
        self._status("websocket", "starting", "开始连接闲鱼消息通道")
        async with websockets.connect(
            self.websocket_url,
            additional_headers=headers,
            user_agent_header=self.user_agent,
            proxy=True if self.use_system_proxy else None,
            ping_interval=None,
        ) as websocket:
            self.ws = websocket
            self._status("websocket", "ok", "闲鱼消息通道已连接")
            await self._register()
            self.last_heartbeat = time.time()
            self.last_heartbeat_response = time.time()
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            try:
                async for raw_message in websocket:
                    await self._handle_raw_message(raw_message, handler)
            finally:
                heartbeat_task.cancel()
                self.ws = None
                self._status("websocket", "closed", "闲鱼消息通道已关闭")

    async def _register(self) -> None:
        assert self.ws is not None
        self._status("register", "starting", "开始注册消息通道")
        register_msg = {
            "lwp": "/reg",
            "headers": {
                "cache-header": "app-key token ua wv",
                "app-key": "444e9908a51d1cb236a27862abc769c9",
                "token": self.current_token,
                "ua": self.user_agent,
                "dt": "j",
                "wv": "im:3,au:3,sy:6",
                "sync": "0,0;0;0;",
                "did": self.device_id,
                "mid": generate_mid(),
            },
        }
        await self.ws.send(json.dumps(register_msg))
        await asyncio.sleep(1)
        ack_msg = {
            "lwp": "/r/SyncStatus/ackDiff",
            "headers": {"mid": generate_mid()},
            "body": [
                {
                    "pipeline": "sync",
                    "tooLong2Tag": "PNM,1",
                    "channel": "sync",
                    "topic": "sync",
                    "highPts": 0,
                    "pts": int(time.time() * 1000) * 1000,
                    "seq": 0,
                    "timestamp": int(time.time() * 1000),
                }
            ],
        }
        await self.ws.send(json.dumps(ack_msg))
        self._status("register", "ok", "消息通道注册完成")

    async def _heartbeat_loop(self) -> None:
        assert self.ws is not None
        while True:
            if time.time() - self.last_heartbeat > self.heartbeat_interval:
                await self.ws.send(json.dumps({"lwp": "/!", "headers": {"mid": generate_mid()}}))
                self.last_heartbeat = time.time()
            if time.time() - self.last_heartbeat_response > (self.heartbeat_interval + self.heartbeat_timeout):
                raise RuntimeError("心跳超时，闲鱼连接断开")
            await asyncio.sleep(1)

    async def _handle_raw_message(self, raw_message: str, handler: MessageHandler) -> None:
        assert self.ws is not None
        message_data = json.loads(raw_message)
        if message_data.get("code") == 200 and message_data.get("headers", {}).get("mid"):
            self.last_heartbeat_response = time.time()
            return

        headers = message_data.get("headers", {})
        if headers.get("mid"):
            ack_headers = {"mid": headers["mid"], "sid": headers.get("sid", "")}
            for key in ("app-key", "ua", "dt"):
                if headers.get(key):
                    ack_headers[key] = headers[key]
            ack = {"code": 200, "headers": ack_headers}
            await self.ws.send(json.dumps(ack))

        if not self._is_sync_package(message_data):
            self._status("message_receive", "skip", "收到非聊天同步包，已跳过")
            return

        payload = message_data["body"]["syncPushPackage"]["data"][0].get("data")
        if not payload:
            self._status("message_receive", "skip", "同步包中没有 data 字段")
            return

        self._status(
            "message_receive",
            "ok",
            "收到闲鱼原始消息",
            payload_length=len(payload),
        )

        try:
            message = decrypt_message(payload)
        except Exception as exc:
            self.logger.warning("解析闲鱼消息失败，已跳过该消息: %s", exc)
            self._dump_raw_message(payload, str(exc))
            self._status("message_parse", "error", f"解析闲鱼消息失败: {exc}")
            return
        self._status("message_parse", "ok", "闲鱼消息解析成功", keys=list(message.keys())[:8])
        chat_message = self._extract_chat_message(message)
        if not chat_message:
            self._status("message_parse", "skip", "解析成功，但不是客户聊天消息")
            return
        self._status(
            "message_dispatch",
            "ok",
            "识别到客户聊天消息",
            chat_id=chat_message.chat_id,
            sender_name=chat_message.sender_name,
            item_id=chat_message.item_id,
        )
        await handler(chat_message)

    def _is_sync_package(self, message_data: dict[str, Any]) -> bool:
        return bool(
            isinstance(message_data, dict)
            and message_data.get("body", {}).get("syncPushPackage", {}).get("data")
        )

    def _extract_chat_message(self, message: dict[str, Any]) -> ChatMessage | None:
        section = self._pick(message, "1", 1)
        if not isinstance(section, dict):
            return None
        reminder = self._pick(section, "10", 10)
        if not isinstance(reminder, dict):
            return None
        content = self._pick(reminder, "reminderContent", "content")
        if not content:
            return None

        created_at_ms = int(self._pick(section, "5", 5, default=0) or 0)
        if created_at_ms and time.time() * 1000 - created_at_ms > self.message_expire_ms:
            self._status(
                "message_parse",
                "skip",
                "消息已过期，已跳过",
                chat_id=str(self._pick(section, "2", 2, default="")),
            )
            return None

        reminder_url = str(self._pick(reminder, "reminderUrl", default=""))
        item_id = ""
        if "itemId=" in reminder_url:
            item_id = reminder_url.split("itemId=")[1].split("&")[0]

        chat_id = str(self._pick(section, "2", 2, default="")).split("@")[0]
        sender_id = str(self._pick(reminder, "senderUserId", default=""))
        sender_name = str(self._pick(reminder, "reminderTitle", default="客户"))
        # 关键字段缺失时不进入自动回复，避免误回系统消息。
        if not chat_id or not sender_id:
            return None
        return ChatMessage(
            chat_id=chat_id,
            item_id=item_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            created_at_ms=created_at_ms or int(time.time() * 1000),
            is_self=sender_id == self.my_id,
        )

    def _pick(self, data: dict[str, Any], *keys: Any, default: Any = None) -> Any:
        """兼容消息字段在数字键与字符串键之间切换的情况。"""
        for key in keys:
            if key in data:
                return data[key]
            if isinstance(key, int):
                text_key = str(key)
                if text_key in data:
                    return data[text_key]
            if isinstance(key, str) and key.isdigit():
                int_key = int(key)
                if int_key in data:
                    return data[int_key]
        return default

    def _status(self, stage: str, status: str, detail: str, **extra: Any) -> None:
        if self.status_callback:
            self.status_callback(stage=stage, status=status, detail=detail, **extra)

    def _dump_raw_message(self, payload: str, error_text: str) -> None:
        if self.diagnostics_dir is None:
            return
        timestamp = int(time.time() * 1000)
        data = {
            "time": timestamp,
            "error": error_text,
            "payload": payload,
        }
        target = self.diagnostics_dir / f"raw-message-{timestamp}.json"
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
