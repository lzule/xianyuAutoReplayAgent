"""Shared types for rag_engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Case:
    case_id: str
    intent: str
    product_hint: str
    user_query: str
    agent_reply: str
    outcome_tag: str = "unknown"
    style_tags: list[str] = field(default_factory=list)
    created_at: str = ""


@dataclass(frozen=True)
class ChatState:
    stage: str = "unknown"
    risk_level: str = "low"
    last_offer_band: str = ""
    open_questions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievalCandidate:
    case: Case
    lexical_score: float
    semantic_score: float = 0.0
    final_score: float = 0.0


@dataclass(frozen=True)
class ReplyDraft:
    reply_text: str
    confidence: float
    references: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GuardrailResult:
    ok: bool
    reply_text: str
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RagDecision:
    action: str
    reply_text: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    fallback_used: bool = False
