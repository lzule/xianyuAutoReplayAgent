"""公共数据结构。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ChatMessage:
    chat_id: str
    item_id: str
    sender_id: str
    sender_name: str
    content: str
    created_at_ms: int
    is_self: bool = False


@dataclass
class QuoteResult:
    service_key: str
    price: int
    summary: str
    needs_handoff: bool = False
    reasons: list[str] = field(default_factory=list)


@dataclass
class ScheduleResult:
    matched: bool
    summary: str
    suggestions: list[str] = field(default_factory=list)
    needs_handoff: bool = False


@dataclass
class Decision:
    action: str
    reply_text: str
    reasons: list[str] = field(default_factory=list)
    quote: QuoteResult | None = None
    schedule: ScheduleResult | None = None
    handoff_required: bool = False
    handoff_summary: str = ""


@dataclass
class ConversationState:
    chat_id: str
    item_id: str
    customer_id: str
    customer_name: str
    status: str
    manual_mode: bool
    last_message: str
    updated_at: str


def utc_now_text() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def to_dict(data: Any) -> dict[str, Any]:
    if hasattr(data, "__dataclass_fields__"):
        return asdict(data)
    return dict(data)
