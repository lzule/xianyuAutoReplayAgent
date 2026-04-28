"""Generate response from reranked candidates."""

from __future__ import annotations

from app.rag_engine.policies.sales_policy import build_system_prompt
from app.rag_engine.providers.llm_openai import OpenAILLMProvider
from app.rag_engine.types import ReplyDraft, RetrievalCandidate


class ReplyGenerator:
    def __init__(self, llm_provider: OpenAILLMProvider | None = None) -> None:
        self.llm_provider = llm_provider

    def generate(
        self,
        *,
        message_text: str,
        item_title: str,
        candidates: list[RetrievalCandidate],
        timeout_seconds: float,
        max_cases_in_prompt: int,
    ) -> ReplyDraft:
        if not candidates:
            return ReplyDraft(reply_text="", confidence=0.0, references=[])

        refs = [candidate.case.case_id for candidate in candidates[:max_cases_in_prompt]]

        if self.llm_provider and self.llm_provider.is_ready():
            case_blocks = []
            for idx, candidate in enumerate(candidates[:max_cases_in_prompt], start=1):
                case = candidate.case
                case_blocks.append(
                    f"案例{idx} 用户问：{case.user_query}\n"
                    f"案例{idx} 你的回复：{case.agent_reply}"
                )
            user_prompt = (
                f"商品标题：{item_title}\n"
                f"客户消息：{message_text}\n\n"
                f"可参考历史案例：\n" + "\n\n".join(case_blocks) +
                "\n\n请给出一条自然、友好、专业、可推进成交的回复。"
            )
            try:
                reply_text = self.llm_provider.generate(
                    system_prompt=build_system_prompt(),
                    user_prompt=user_prompt,
                    timeout_seconds=max(1.0, timeout_seconds),
                )
            except Exception:
                reply_text = ""
            if reply_text:
                return ReplyDraft(reply_text=reply_text, confidence=0.82, references=refs)

        best = candidates[0].case
        fallback = best.agent_reply
        if not fallback.endswith(("。", "！", "?", "？")):
            fallback += "。"
        fallback += "你这边也可以把当前具体情况发我，我帮你按这个方向快速判断。"
        return ReplyDraft(reply_text=fallback, confidence=0.63, references=refs)
