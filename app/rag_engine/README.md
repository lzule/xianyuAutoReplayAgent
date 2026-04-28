# rag_engine

独立的 RAG 业务模块，负责：

- 案例召回（retrieve）
- 候选重排（rerank）
- 回复生成（generate）
- 回复守卫（guardrail）
- 灰度与回退（facade）

主业务通过 `RagEngine.reply(...)` 接入，避免把检索细节散落到 `dialog`/`core`。
