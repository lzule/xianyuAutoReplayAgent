"""Retrieve candidates from case index."""

from __future__ import annotations

from app.rag_engine.providers.embedding_openai import OpenAIEmbeddingProvider
from app.rag_engine.stores.vector_store import VectorStore
from app.rag_engine.types import RetrievalCandidate


class Retriever:
    def __init__(self, store: VectorStore, embedding_provider: OpenAIEmbeddingProvider | None = None) -> None:
        self.store = store
        self.embedding_provider = embedding_provider

    def retrieve(self, query: str, top_k: int = 30) -> list[RetrievalCandidate]:
        lexical_candidates = self.store.lexical_search(query=query, top_k=max(top_k * 2, top_k))
        if not lexical_candidates:
            return []
        if not self.embedding_provider or not self.embedding_provider.is_ready():
            return lexical_candidates[:top_k]
        try:
            query_vecs = self.embedding_provider.embed_texts([query], timeout_seconds=2.0)
            if not query_vecs:
                return lexical_candidates[:top_k]
            candidate_texts = [
                f"{item.case.user_query} {item.case.agent_reply} {item.case.product_hint}"
                for item in lexical_candidates
            ]
            case_vecs = self.embedding_provider.embed_texts(candidate_texts, timeout_seconds=3.5)
            if len(case_vecs) != len(lexical_candidates):
                return lexical_candidates[:top_k]
            merged = self.store.apply_semantic_scores(lexical_candidates, query_vecs[0], case_vecs)
            return merged[:top_k]
        except Exception:
            return lexical_candidates[:top_k]
