# RAG Engine Phase 1 实施（独立模块）

## 背景

- 需要把“像你聊天 + 可促单”的能力从规则引擎中独立出来，形成可维护、可灰度、可回退的模块。

## 变更内容

- 新增独立模块 `app/rag_engine/`：
  - `facade.py`（统一入口）
  - `types.py`、`config.py`
  - `pipeline/`（retrieve/rerank/generate/guardrail）
  - `providers/`（OpenAI 兼容 embedding/llm）
  - `stores/`（cases/vector/cache）
  - `observability/audit_logger.py`
- 新增配置：`configs/rag/default.yaml`
- 新增样本文件：`knowledge/cases/rag_cases.jsonl`（脱敏示例）
- 新增样本构建脚本：`scripts/build_rag_cases.py`
- 接入主流程：
  - `BotApplication` 初始化并注入 `RagEngine`
  - `DialogService.decide` 在高风险判断后尝试 RAG，失败回退旧逻辑
- 新增测试：`tests/test_rag_engine.py`

## 配置与接口影响

- 新增接口：`RagEngine.reply(...)`
- `DialogService.decide(...)` 新增可选参数：`chat_id`, `chat_state`
- 新增配置文件：`configs/rag/default.yaml`

## 验证结果

- 已执行：
  - `bash scripts/privacy_scan.sh`（通过）
  - `python -m compileall app`（通过）
  - `bash scripts/preflight_check.sh --skip-tests`（通过）
- 备注：
  - `pytest -q` 当前环境不可用（`pytest: command not found`），因此未执行单测。

## 风险与回滚

- 风险：未配置模型 API 时，RAG 会使用案例回放式回复，效果低于完整 LLM 生成。
- 回滚：
  - 将 `configs/rag/default.yaml` 的 `enabled` 设为 `false`；或
  - 回退本次提交。
