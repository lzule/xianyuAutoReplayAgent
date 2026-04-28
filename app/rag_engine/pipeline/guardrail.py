"""Reply guardrail."""

from __future__ import annotations

from app.rag_engine.types import GuardrailResult


class Guardrail:
    RISKY_PROMISES = ["保证", "绝对", "100%", "包过", "一定搞定", "肯定没问题"]
    RUDE_WORDS = ["你不懂", "别问", "废话", "自己看"]

    def validate(self, reply_text: str) -> GuardrailResult:
        text = (reply_text or "").strip()
        if not text:
            return GuardrailResult(
                ok=False,
                reply_text="收到，我先帮你核对关键信息，再给你一个稳妥方案。",
                reasons=["空回复"],
            )

        reasons: list[str] = []
        if any(token in text for token in self.RISKY_PROMISES):
            reasons.append("承诺风险")
        if any(token in text for token in self.RUDE_WORDS):
            reasons.append("语气风险")

        if len(text) > 260:
            text = text[:260].rstrip() + "…"
            reasons.append("长度裁剪")

        if reasons:
            safe_text = "我先帮你把关键信息核对清楚，再给你一个稳妥可执行的方案，避免走弯路。"
            return GuardrailResult(ok=False, reply_text=safe_text, reasons=reasons)

        return GuardrailResult(ok=True, reply_text=text, reasons=[])
