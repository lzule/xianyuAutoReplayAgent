"""检查闲鱼 Cookie、Token 和消息通道是否可用。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.channel.xianyu_client import XianyuChannelClient
from app.core.settings import load_settings


async def _ignore_message(message: object) -> None:
    # 自检脚本只验证连接，不在这里处理或回复任何客户消息。
    return None


async def main() -> None:
    settings = load_settings()
    events: list[dict] = []
    client = XianyuChannelClient(
        settings.integration.cookies_str,
        settings.runtime.websocket_url,
        settings.runtime.heartbeat_interval,
        settings.runtime.heartbeat_timeout,
        settings.runtime.message_expire_ms,
        use_system_proxy=settings.runtime.use_system_proxy,
        user_agent=settings.runtime.xianyu_user_agent,
        status_callback=lambda **kwargs: events.append(kwargs),
    )

    print("Cookie 检查:", client.api.get_cookie_health())
    try:
        await asyncio.wait_for(client._connect_once(_ignore_message), timeout=8)
    except TimeoutError:
        print("消息通道检查: 已连上，8 秒内未断开")
    except Exception as exc:
        print(f"消息通道检查: 失败 - {exc}")

    print("最近事件:")
    for event in events[-10:]:
        print(f"- {event.get('stage')} | {event.get('status')} | {event.get('detail')}")


if __name__ == "__main__":
    asyncio.run(main())
