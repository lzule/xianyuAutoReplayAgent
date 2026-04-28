"""Facade entrypoint for rag engine."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from app.core.settings import ModelSettings
from app.rag_engine.config import RagSettings, load_rag_settings
from app.rag_engine.observability.audit_logger import AuditLogger
from app.rag_engine.pipeline.generate import ReplyGenerator
from app.rag_engine.pipeline.guardrail import Guardrail
from app.rag_engine.pipeline.rerank import Reranker
from app.rag_engine.pipeline.retrieve import Retriever
from app.rag_engine.providers.embedding_openai import OpenAIEmbeddingProvider
from app.rag_engine.providers.llm_openai import OpenAILLMProvider
from app.rag_engine.stores.cache_store import TTLCache
from app.rag_engine.stores.case_store import CaseStore
from app.rag_engine.stores.vector_store import VectorStore
from app.rag_engine.types import ChatState, RagDecision


class RagEngine:
    def __init__(
        self,
        *,
        config_path: Path,
        cases_path: Path,
        model_settings: ModelSettings,
        audit_path: Path,
    ) -> None:
        self.config_path = config_path
        self.cases_path = cases_path
        self.model_settings = model_settings
        self.settings: RagSettings = load_rag_settings(config_path)

        self.case_store = CaseStore(cases_path)
        self.vector_store = VectorStore(self.case_store.cases)
        self.embedding_provider = OpenAIEmbeddingProvider(
            api_key=model_settings.api_key,
            base_url=model_settings.base_url,
            model_name=model_settings.model_name,
        )
        self.llm_provider = OpenAILLMProvider(
            api_key=model_settings.api_key,
            base_url=model_settings.base_url,
            model_name=model_settings.model_name,
        )
        self.retriever = Retriever(self.vector_store, self.embedding_provider)
        self.reranker = Reranker()
        self.generator = ReplyGenerator(self.llm_provider)
        self.guardrail = Guardrail()
        self.cache = TTLCache(ttl_seconds=90.0, max_items=512)
        self.audit = AuditLogger(audit_path, enabled=self.settings.audit_enabled)

    def reload(self) -> None:
        self.settings = load_rag_settings(self.config_path)
        self.case_store.reload()
        self.vector_store = VectorStore(self.case_store.cases)
        self.retriever = Retriever(self.vector_store, self.embedding_provider)
        self.audit.enabled = self.settings.audit_enabled

    def is_enabled_for_chat(self, chat_id: str) -> bool:
        if not self.settings.enabled:
            return False
        if self.settings.gray_ratio >= 1.0:
            return True
        if self.settings.gray_ratio <= 0.0:
            return False
        raw = hashlib.md5(chat_id.encode("utf-8")).hexdigest()[:8]
        ratio = int(raw, 16) / 0xFFFFFFFF
        return ratio < self.settings.gray_ratio

    def reply(
        self,
        *,
        chat_id: str,
        message_text: str,
        item_title: str,
        chat_state: ChatState | None = None,
    ) -> RagDecision:
        if not self.is_enabled_for_chat(chat_id):
            return RagDecision(
                action="skip",
                reply_text="",
                confidence=0.0,
                reasons=["rag_disabled_or_not_in_gray"],
                fallback_used=True,
            )
        if not self.case_store.cases:
            return RagDecision(
                action="fallback",
                reply_text="",
                confidence=0.0,
                reasons=["rag_no_cases"],
                fallback_used=True,
            )

        key = f"{chat_id}|{message_text}|{item_title}"
        cached = self.cache.get(key)
        if cached:
            return cached

        state = chat_state or ChatState()
        started = time.monotonic()
        candidates = self.retriever.retrieve(query=message_text, top_k=self.settings.recall_k)
        if not candidates:
            result = RagDecision(
                action="fallback",
                reply_text="",
                confidence=0.0,
                reasons=["rag_no_retrieval_match"],
                fallback_used=True,
            )
            self.cache.set(key, result)
            return result

        reranked = self.reranker.rerank(
            query=message_text,
            item_title=item_title,
            candidates=candidates,
            top_k=self.settings.rerank_k,
            chat_state=state,
        )
        if not reranked:
            result = RagDecision(
                action="fallback",
                reply_text="",
                confidence=0.0,
                reasons=["rag_no_rerank_match"],
                fallback_used=True,
            )
            self.cache.set(key, result)
            return result

        best_score = reranked[0].final_score
        if best_score < self.settings.min_score:
            result = RagDecision(
                action="fallback",
                reply_text="",
                confidence=best_score,
                reasons=["rag_score_below_threshold"],
                fallback_used=True,
            )
            self.cache.set(key, result)
            return result

        elapsed = (time.monotonic() - started) * 1000
        if elapsed >= self.settings.hard_timeout_ms:
            result = RagDecision(
                action="fallback",
                reply_text="",
                confidence=0.0,
                reasons=["rag_hard_timeout"],
                fallback_used=True,
            )
            self.cache.set(key, result)
            return result

        if elapsed >= self.settings.soft_timeout_ms:
            safe_reply = "收到，我先把你的情况快速核对一下，马上给你一个可执行建议。"
            result = RagDecision(
                action="safe_reply",
                reply_text=safe_reply,
                confidence=0.4,
                reasons=["rag_soft_timeout"],
                fallback_used=False,
            )
            self.audit.log(
                {
                    "chat_id": chat_id,
                    "action": result.action,
                    "reasons": result.reasons,
                    "refs": [],
                }
            )
            self.cache.set(key, result)
            return result

        remaining = max(1.0, (self.settings.hard_timeout_ms - elapsed) / 1000.0)
        draft = self.generator.generate(
            message_text=message_text,
            item_title=item_title,
            candidates=reranked,
            timeout_seconds=remaining,
            max_cases_in_prompt=self.settings.max_cases_in_prompt,
        )
        guard = self.guardrail.validate(draft.reply_text)
        action = "reply" if guard.ok else "safe_reply"
        reasons = ["rag_hit"]
        if not guard.ok:
            reasons.extend(guard.reasons)

        result = RagDecision(
            action=action,
            reply_text=guard.reply_text,
            confidence=draft.confidence,
            reasons=reasons,
            references=draft.references,
            fallback_used=False,
        )
        self.audit.log(
            {
                "chat_id": chat_id,
                "action": result.action,
                "reasons": result.reasons,
                "confidence": result.confidence,
                "refs": result.references,
            }
        )
        self.cache.set(key, result)
        return result
