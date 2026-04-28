# External Agent Core HTTP Integration

## 背景
- 独立 `agent+r ag` 仓库先行开发，需要主项目通过 HTTP 契约回接，并保留本地规则回退。

## 变更内容
- 新增 `app/dialog/agent_core_client.py`：外部 Agent Core HTTP client。
- 扩展配置：`AGENT_CORE_ENABLED`、`AGENT_CORE_TIMEOUT_MS`、`AGENT_CORE_BASE_URL`。
- `DialogService` 优先调用外部服务，失败自动回退本地流程。
- 主流程传入客户会话上下文 `conversation_history`。
- 新增测试：`tests/test_dialog_agent_core.py`。

## 配置与接口影响
- `DialogService.decide` 新增：`item_id`, `conversation_history`, `meta`。
- `BotStore` 新增：`get_chat_history`。

## 验证结果
- 已执行：
  - `bash scripts/privacy_scan.sh`（通过）
  - `python -m compileall app tests`（通过）
  - `bash scripts/preflight_check.sh --skip-tests`（通过）
- 备注：
  - 当前环境无 `pytest` 模块，未执行 `python -m pytest -q`。

## 风险与回滚
- 风险：外部服务不可用时回复质量回落到本地规则。
- 回滚：关闭 `AGENT_CORE_ENABLED` 即可即时回退。
