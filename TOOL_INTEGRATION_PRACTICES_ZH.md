# 数字化工具接入 nanobot / nanobot-internal 实践方案

本文给出一套可落地的“四步法”，帮助把已有的数据分析、预测、仿真类 API 服务接入到 nanobot 体系。

## 1) 对原有工具二次开发：让接口更 AI Friendly

核心原则：**模型更擅长“结构化、可枚举、可校验”的接口**。

- **接口命名语义化**：如 `get_sales_stats`、`forecast_demand`、`run_simulation`，避免 `doTask1` 这类弱语义名称。
- **入参强约束**：使用 JSON Schema/Pydantic 描述字段、类型、枚举、默认值、边界值（例如 `horizon_days: 1~90`）。
- **错误可机器处理**：统一错误结构：`code/message/retriable/suggestion`，避免只返回文本栈。
- **响应分层**：
  - `summary`（给模型用于直接回答用户）
  - `artifacts`（图表 URL、报表文件路径）
  - `raw`（原始明细，便于追溯）
- **幂等与可追踪**：支持 `request_id/trace_id`，日志中贯穿上下游。
- **异步任务标准化**：长任务统一为 `submit -> status -> result` 三段式，避免单接口超时。
- **提示友好字段**：在响应里带 `next_actions`（建议下一步可调用的接口），可显著提升多步编排稳定性。

建议优先补齐 OpenAPI 文档，并在每个 endpoint 中补“业务语义说明 + 示例请求/响应”。

## 2) 将部署好的 API 接入 nanobot（主 Agent）

nanobot 主 Agent 已支持工具注册与执行链路（含 trace），建议两种接入方式：

### 方式 A：封装为 nanobot 原生 Tool（推荐）

- 在 `nanobot/agent/tools/` 下新增工具实现（继承基础工具约定）。
- 在 `nanobot/agent/tools/registry.py` 注册工具名与 schema。
- 通过 `AgentLoop` 自动参与 tool-calling。

适用：高频、稳定、需要和现有工具协同编排的能力。

### 方式 B：封装为 MCP 服务后接入

- 将现有 API 包一层 MCP Server。
- 在配置中增加 `tools.mcpServers`，让 Agent 通过 MCP 发现并调用。

适用：已有工具生态多、希望跨 Agent 复用、希望弱耦合接入。

> 生产建议：无论 A/B，都应把 API 鉴权 token 放在环境变量，不在 prompt 或 skill 中明文出现。

## 3) 将部署好的 API 接入 nanobot-internal

`nanobot-internal` 的定位是“企业内网编排网关”，非常适合把多工具流程统一成一个编排入口。

实践步骤：

1. 在 `nanobot/internal_orchestrator/tools.py` 中增加 API 适配函数（一个函数对应一个业务能力）。
2. 在工具描述中写清楚参数 schema 与调用示例，让 LLM 更容易正确发起 tool call。
3. 在 `nanobot/internal_orchestrator/agent.py` 的执行路径中补充：
   - 超时与重试（尤其是仿真类长任务）
   - 错误归一化（统一给 LLM 可理解的错误对象）
   - trace 字段增强（业务主键、耗时、状态）
4. 通过 `nanobot-internal` 的 Dashboard + `/api/v1/traces` 观察编排质量，迭代提示词和 schema。

建议把“复杂业务流程”沉淀为后端组合 API，而不是把所有流程复杂度压给模型在单轮内完成。

## 4) 将 API 使用流程写成 Skill，集成到 nanobot Agent

技能本质是“可复用作业 SOP（标准作业流程）”。

推荐模板：

- `name`: 例如 `factory-simulation-assistant`
- `description`: 触发条件（如“产线预测、仿真、产能评估”）
- 正文包含：
  1. 前置检查（确认时间区间、工厂/设备 ID）
  2. 调用顺序（先统计，再预测，最后仿真）
  3. 失败兜底（缺数据时回退到统计口径）
  4. 输出格式（结论 + 风险 + 建议动作）

这样可以把“工具调用顺序”和“回答格式”显式固定，降低模型漂移。

---

## 推荐落地路线（两周版本）

- **第 1 周**：改造 3 个核心 API（统计/预测/仿真）为 AI-friendly schema，并打通 trace_id。
- **第 2 周**：
  - 接入 nanobot（Tool/MCP 二选一）
  - 接入 nanobot-internal（编排网关）
  - 编写 1~2 个业务 Skill（如“日报分析”“仿真评估”）
  - 用 dashboard 观察调用成功率与重试率并迭代。

这套方案能确保：**接口可调用、流程可编排、行为可追踪、经验可沉淀**。
