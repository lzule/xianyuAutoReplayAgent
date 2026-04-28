# Dual Repo Handoff Playbook

## 背景
- 采用双仓并行开发：主仓负责闲鱼通道与兜底，独立仓负责 Agent+RAG。

## 变更内容
- 新增主仓交接手册：`docs/agent-core-integration-handoff.md`。
- 明确“当前不移除主仓本地 agent/rag，仅在达标后再移除”。
- 明确双仓并行、灰度、最终合并三阶段流程。

## 验证结果
- 文档完整性检查：已完成。

## 风险与回滚
- 风险：双仓版本漂移。
- 处理：坚持 API 契约兼容与变更留痕。
