# nanobot 内网离线化部署与接口接入方案

本文给出可落地方案，覆盖：

1. `nanobot/agent/tools` 工具本地化整理。
2. `nanobot/application/orchestration/environment.py` 的改造说明。
3. 现有程序接口（可二开 API）如何改造成更适配 agent，并接入本项目的步骤。

## 1. 工具清单与本地化策略

当前目录：`nanobot/agent/tools`

- `filesystem.py`：本地读写/编辑/目录列举（已天然本地化）。
- `shell.py`：本地命令执行（已本地化，需约束权限）。
- `md_api.py`：原先仅远程 md-api；已改造为支持 `local/http` 双模式。
- `web.py`：原先依赖 Brave 外网搜索；已改造为支持本地检索端点优先。
- `mcp.py`：可接入本地/内网 MCP 服务。
- `cron.py`、`message.py`、`spawn.py`：编排层与消息能力，通常不依赖外网。

### 1.1 推荐离线能力分级

- **L1（纯离线）**：`filesystem` + `shell` + `md_read/md_write(local)`。
- **L2（内网增强）**：L1 + `web_search(local)` + 内网 MCP。
- **L3（可控半离线）**：L2 + 特定白名单代理能力（不建议默认开启）。

### 1.2 环境变量建议

- `MD_API_MODE=local`（默认建议）。
- `MD_API_LOCAL_BASE_DIR=/data/nanobot/workspace`（可选；未配置则跟随 workspace）。
- `LOCAL_SEARCH_API_URL=http://intranet-search.local/api/search`（使用你们的内网检索网关）。
- `NANOBOT_DISABLE_WEB_TOOLS=true`（若完全禁用网页抓取）。

## 2. 本次代码改造点

## 2.1 `md_api.py` 双模式化

- 新增 `mode`：
  - `local`：直接读写本地 markdown 文件。
  - `http`：走原有 md-api 服务。
- 新增安全路径约束：防止 `../` 越权访问。
- `MDReadTool`/`MDWriteTool` 支持通过构造参数或环境变量注入：`mode/base_url/token/local_base_dir`。

## 2.2 `web.py` 本地检索优先

- `web_search` 增加本地接口模式：
  - 若设置 `LOCAL_SEARCH_API_URL`，优先调用本地检索 API。
  - 否则回退 Brave（有 `BRAVE_API_KEY` 时）。
- 未配置任一检索后端时，给出明确错误提示。

## 2.3 `environment.py` 的离线默认策略

- 默认将 `md_read/md_write` 以 `MD_API_MODE=local` 注册，根目录跟随 agent workspace。
- 增加 `NANOBOT_DISABLE_WEB_TOOLS` 开关，离线场景可禁用 `web_search/web_fetch`。
- 保留 MCP 懒加载机制，方便挂载你们内网工具服务。

## 3. 你已有程序接口时，API 如何改造更适配 Agent

如果你已有 API，并可二开，建议遵循以下“Agent 友好”规范。

## 3.1 设计目标

- **低歧义**：参数 schema 清晰、约束明确。
- **幂等可重试**：网络抖动/模型误触发时不会造成副作用扩大。
- **可观测**：返回 trace id、耗时、状态码、错误类型。
- **可裁剪输出**：支持摘要字段，防止 token 爆炸。

## 3.2 推荐 API 契约（工具型）

建议统一 `POST /tool/<name>` 或网关统一入口 `POST /api/tools/invoke`。

请求：

```json
{
  "request_id": "uuid",
  "tool": "query_data_statistics",
  "args": {"dataset": "sales", "date": "2026-03-03"},
  "dry_run": false,
  "timeout_ms": 10000
}
```

返回：

```json
{
  "ok": true,
  "data": {"total": 12345, "trend": "+2.4%"},
  "summary": "sales 当日总量 12345，环比 +2.4%",
  "error": null,
  "trace_id": "trc_xxx",
  "latency_ms": 83
}
```

错误返回保持结构一致：

```json
{
  "ok": false,
  "data": null,
  "summary": "参数 date 格式错误，应为 YYYY-MM-DD",
  "error": {"code": "INVALID_ARGUMENT", "detail": "..."},
  "trace_id": "trc_xxx",
  "latency_ms": 12
}
```

## 3.3 对 Agent 更友好的改造建议

- 每个接口提供 machine-readable schema（OpenAPI/JSON Schema）。
- 参数强类型化：枚举、范围、必填项严格化。
- 支持 `dry_run`（高风险操作先预演）。
- 返回中加入 `summary`（给模型直接引用）。
- 长数据分页：`page/page_size/next_cursor`。
- 统一错误码：`INVALID_ARGUMENT`、`UNAUTHORIZED`、`TIMEOUT`、`UPSTREAM_ERROR`。
- 统一鉴权：服务账号 + 最小权限 + IP 白名单。

## 4. 接入 nanobot agent 的实施步骤

## 4.1 方式 A：通过 MCP 接入（推荐）

1. 将现有服务包装为 MCP server（stdio 或 http streamable）。
2. 在 `~/.nanobot/config.json` 的 `tools.mcpServers` 增加配置。
3. 启动 `nanobot agent`，验证工具自动注册。
4. 在技能提示词中显式约束工具调用顺序。

优点：与主 Agent 解耦，扩展性最好。

## 4.2 方式 B：直接实现 Tool 类

1. 在 `nanobot/agent/tools/` 新增 `xxx.py`，继承 `Tool`。
2. 在 `environment.py` 中注册该工具。
3. 为参数补全 JSON Schema，增加输入校验。
4. 运行回归测试。

优点：简单直接；缺点：升级时耦合主仓库。

## 4.3 方式 C：复用 `internal_orchestrator` 网关

1. 在 `nanobot/internal_orchestrator/tools.py` 注册企业 API handler。
2. 由 orchestrator 作为统一工具代理层。
3. 主 agent 通过 MCP/http 工具连接 orchestrator。

优点：统一鉴权、审计、限流和回放。

## 5. 上线检查清单（内网）

- [ ] 关闭外网依赖（Brave、公网 URL 抓取）。
- [ ] workspace 权限隔离（只读/可写目录分离）。
- [ ] 工具超时与重试策略。
- [ ] 关键写操作需要审批或 `dry_run` 二次确认。
- [ ] trace 日志留存（session_id / tool / args 摘要 / latency / result）。
- [ ] 灰度发布：先只读工具，再开放写工具。

---

如果你愿意，我下一步可以按你的现有 API 列表（接口名+入参+出参）直接帮你产出：

1) 对应的 Tool schema 草案；
2) MCP server 映射模板；
3) 最小可运行接入代码（可直接合入本仓库）。
