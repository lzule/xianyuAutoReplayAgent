"""Candidate reranking."""

from __future__ import annotations

from app.rag_engine.policies.sales_policy import classify_intent
from app.rag_engine.types import ChatState, RetrievalCandidate


class Reranker:
    def rerank(
        self,
        query: str,
        item_title: str,
        candidates: list[RetrievalCandidate],
        top_k: int,
        chat_state: ChatState,
    ) -> list[RetrievalCandidate]:
        if not candidates:
            return []
        target_intent = classify_intent(query)
        ranked: list[RetrievalCandidate] = []
        lowered_item_title = item_title.lower()
        for candidate in candidates:
            case = candidate.case
            base = candidate.final_score
            intent_bonus = 1.0 if case.intent == target_intent else 0.0
            product_bonus = 1.0 if case.product_hint and case.product_hint.lower() in lowered_item_title else 0.0
            outcome_bonus = 1.0 if case.outcome_tag in {"deal", "positive", "成交"} else 0.0
            stage_bonus = 1.0 if chat_state.stage and chat_state.stage in case.style_tags else 0.0
            final = (
                0.45 * base
                + 0.25 * intent_bonus
                + 0.15 * product_bonus
                + 0.10 * outcome_bonus
                + 0.05 * stage_bonus
            )
            ranked.append(
                RetrievalCandidate(
                    case=case,
                    lexical_score=candidate.lexical_score,
                    semantic_score=candidate.semantic_score,
                    final_score=final,
                )
            )
        ranked.sort(key=lambda item: item.final_score, reverse=True)
        return ranked[:top_k]
