# Changelog

All notable changes to this project will be documented in this file.

## 2026-04-28

- Added independent `rag_engine` module with retrieve/rerank/generate/guardrail pipeline.
- Added RAG config, seed cases, and local case-building script.
- Wired `rag_engine` into dialog decision flow with gray rollout and fallback support.
- Added phase implementation note under `docs/changes/`.
- Added change governance and release safety process documents.
- Added privacy scanning script and release preflight script.
- Added `docs/changes/` records, including this rollout note.
- Hardened `.gitignore` for sensitive chat/runtime exports.
