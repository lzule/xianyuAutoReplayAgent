# 变更留痕与隐私发布规范落地

## 背景

- 项目需要把“每次改动有历史记录、确认后可推送、隐私不泄露”变成固定流程，而不是口头约定。

## 变更内容

- 新增 `docs/change-and-release-process.md`，定义开发到推送的强制步骤。
- 新增 `docs/changes/README.md`，定义变更记录模板与命名规则。
- 新增 `scripts/privacy_scan.sh`，用于扫描敏感信息泄露风险。
- 新增 `scripts/preflight_check.sh`，统一执行隐私扫描与可选测试。
- 新增 `CHANGELOG.md`，记录可读的变更摘要。
- 更新 `.gitignore`，屏蔽本地敏感数据与运行导出目录。

## 配置与接口影响

- 无业务接口变更。
- 新增两个本地运维脚本：
  - `scripts/privacy_scan.sh`
  - `scripts/preflight_check.sh`

## 验证结果

- 已执行：
  - `bash scripts/privacy_scan.sh`（通过）
  - `bash scripts/preflight_check.sh --skip-tests`（通过）
  - `bash scripts/preflight_check.sh`（通过，`pytest` 未安装，测试步骤自动跳过）

## 风险与回滚

- 风险：敏感词规则可能出现误报，需根据实际仓库内容微调白名单。
- 回滚：删除新增文档与脚本，恢复 `.gitignore` 变更，并从 `CHANGELOG.md` 移除对应条目。
