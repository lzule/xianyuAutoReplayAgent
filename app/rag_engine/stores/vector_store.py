"""In-memory vector/lexical index."""

from __future__ import annotations

import math
import re

from app.rag_engine.types import Case, RetrievalCandidate


def _tokenize(text: str) -> set[str]:
    parts = re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]", text.lower())
    return {p for p in parts if p}


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


class VectorStore:
    def __init__(self, cases: list[Case]) -> None:
        self._cases = cases
        self._tokens: dict[str, set[str]] = {}
        for case in cases:
            text = f"{case.user_query} {case.agent_reply} {case.product_hint} {case.intent}"
            self._tokens[case.case_id] = _tokenize(text)

    def lexical_search(self, query: str, top_k: int) -> list[RetrievalCandidate]:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        out: list[RetrievalCandidate] = []
        for case in self._cases:
            c_tokens = self._tokens.get(case.case_id, set())
            inter = len(q_tokens & c_tokens)
            if inter == 0:
                continue
            union = len(q_tokens | c_tokens)
            score = inter / union if union else 0.0
            out.append(RetrievalCandidate(case=case, lexical_score=score, final_score=score))
        out.sort(key=lambda item: item.final_score, reverse=True)
        return out[:top_k]

    def apply_semantic_scores(
        self,
        candidates: list[RetrievalCandidate],
        query_vector: list[float],
        case_vectors: list[list[float]],
    ) -> list[RetrievalCandidate]:
        if not candidates or not query_vector or len(candidates) != len(case_vectors):
            return candidates
        scored: list[RetrievalCandidate] = []
        for candidate, case_vector in zip(candidates, case_vectors):
            sem = _cosine(query_vector, case_vector)
            final_score = (0.6 * candidate.lexical_score) + (0.4 * sem)
            scored.append(
                RetrievalCandidate(
                    case=candidate.case,
                    lexical_score=candidate.lexical_score,
                    semantic_score=sem,
                    final_score=final_score,
                )
            )
        scored.sort(key=lambda item: item.final_score, reverse=True)
        return scored
