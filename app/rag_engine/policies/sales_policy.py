"""Intent and prompt helpers for sales conversation."""

from __future__ import annotations


def classify_intent(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ["价格", "报价", "收费", "多少钱", "便宜", "优惠", "费用"]):
        return "pricing"
    if any(keyword in lowered for keyword in ["时间", "什么时候", "预约", "有空", "安排"]):
        return "schedule"
    if any(keyword in lowered for keyword in ["部署", "环境", "报错", "版本", "兼容"]):
        return "technical"
    return "general"


def build_system_prompt() -> str:
    return (
        "你是一个专业、友好、注重成交效率的技术服务顾问。"
        "回复要简洁、自然，先回答客户核心问题，再推进下一步。"
        "不要夸大承诺，不要保证100%结果，不要给超权限承诺。"
    )
