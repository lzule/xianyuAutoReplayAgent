# Agent Core 集成交接手册（主项目）

## 当前结构（2026-04-28）

- 本仓库负责：
  - 闲鱼通道接入（收消息、发消息）
  - 会话状态、人工接管、通知与后台
  - 业务兜底规则（FAQ/报价/预约/转人工）
- 外部仓库 `xianyu-sales-agent-core` 负责：
  - Agent + RAG 回复决策
  - 会话回放验证
  - 独立 HTTP API 服务

## 当前调用链

1. `XianyuChannelClient` 收到客户消息
2. `BotApplication` 落库消息并取该 `chat_id` 历史上下文
3. `DialogService` 优先调用外部 `agent_core`（HTTP）
4. 外部失败或不可用时，自动回退本地决策逻辑

## 是否应移除主项目内 agent/rag

结论：**当前不移除**。

原因：
- 仍需本地兜底，避免外部服务异常导致业务中断。
- 分仓阶段需要随时可回退。

移除条件（全部满足后再做）：
- 外部服务连续稳定运行 >= 7 天。
- 主项目灰度会话中，外部成功率 >= 99%。
- 关键指标（回复时延、转人工命中、客户负反馈）达到目标。
- 已验证断连回退策略（含超时、网络异常、接口错误）。

## 分开开发与合并流程

### 阶段 A：并行开发
- 在 `xianyu-sales-agent-core` 迭代 Agent/RAG。
- 在本仓库仅维护 HTTP 适配层与兜底逻辑。

### 阶段 B：灰度接入
- 配置：
  - `AGENT_CORE_ENABLED=true`
  - `AGENT_CORE_BASE_URL=http://127.0.0.1:8780`
  - `AGENT_CORE_TIMEOUT_MS=6000`
- 按会话灰度放量，记录成功率与回退率。

### 阶段 C：最终合并
- 若选择“逻辑合并到主仓”：
  1. 冻结外部仓接口版本
  2. 镜像迁移 `agent_core` 关键模块到主仓 `app/agent_core/`
  3. 保留 HTTP 客户端一个迭代周期用于回滚
  4. 通过验收后再删除旧本地 rag 分支逻辑
- 若选择“长期双仓”：
  - 主仓长期仅保留 HTTP client + fallback，不做代码合并。

## 发布前检查

- `bash scripts/privacy_scan.sh`
- `bash scripts/preflight_check.sh --skip-tests`
- 外部服务 `GET /v1/health` 返回 `ok=true`
- 本地模拟 `/api/debug/simulate` 同时验证：
  - 外部命中路径
  - 外部失败回退路径
