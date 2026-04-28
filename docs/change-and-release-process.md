# 变更留痕与安全发布流程

本项目所有代码改动都必须遵循以下顺序，避免漏测、漏文档和隐私泄露。

## 1) 开始改动前

1. 创建分支：`feature/<topic>` 或 `fix/<topic>`。
2. 明确本次目标、影响范围、回滚策略。

## 2) 开发与验证

1. 完成代码或配置改动。
2. 运行本地检查：
   - `bash scripts/privacy_scan.sh`
   - `bash scripts/preflight_check.sh --skip-tests`（仅快速检查）
   - 或 `bash scripts/preflight_check.sh`（包含测试）

## 3) 变更留痕（强制）

1. 在 `docs/changes/` 新建一条记录：
   - 文件名：`YYYY-MM-DD-<topic>.md`
2. 文档必须包含以下字段：
   - 背景
   - 变更内容
   - 配置与接口影响
   - 验证结果
   - 风险与回滚
3. 更新 `CHANGELOG.md`，写一条摘要并指向对应记录。

## 4) 提交前隐私要求（强制）

1. 禁止提交真实凭证：
   - `.env`
   - Cookie（如 `_m_h5_tk`, `cookie2`, `sgcookie`, `unb`, `cna`）
   - Webhook（如 `open.feishu.cn`）
2. 禁止提交原始聊天数据或客户隐私：
   - `chat/` 原始消息
   - 手机号、身份证号、精确地址、订单号等敏感信息
3. 仅允许提交脱敏后的知识或样本。

## 5) 提交与推送

1. `git add` 只添加本次改动和对应文档。
2. 提交信息建议：
   - `feat: ...`
   - `fix: ...`
   - `docs: ...`
3. 推送到 GitHub 前再次执行：
   - `bash scripts/preflight_check.sh`

## 6) 线上异常回滚

1. 发现异常先关闭自动回复（或切人工模式）。
2. 使用上一稳定提交回滚。
3. 在新的 `docs/changes/...` 记录回滚原因与处置结果。
