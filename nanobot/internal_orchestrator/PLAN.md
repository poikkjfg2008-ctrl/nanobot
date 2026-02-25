# Nanobot 内网编排层简化改造方案（高完成度实施稿）

## 1. 目标与约束

### 1.1 场景目标
- 将现有部门 API（统计分析 / 深度学习预测 / 仿真）统一为“大模型可调用工具层”。
- 以 `nanobot` 的轻量设计为基础，保留“工具编排核心”，去除与企业场景不相关的 C 端能力。
- 在**仅内网可用、基座模型能力接近开源模型**的前提下，保障工具调用稳定性和可运维性。

### 1.2 关键约束
- 外网访问受限，不能依赖公网 SaaS。
- 模型 function-calling 稳定性弱，需要容错。
- 首期快速上线，先以 mock + 标准 API 网关方式打通，逐步替换为真实服务。

---

## 2. 与原仓库的关系（做减法）

本次实现新增 `nanobot/internal_orchestrator/`，作为企业内网版“最小可用编排层”。

### 2.1 保留
- 多轮 Agent Loop 的核心思想（模型决策 -> 工具执行 -> 回传工具结果）。
- 工具 Schema 描述 + 统一注册中心。
- JSON 修复容错（`json-repair`）以适配较弱模型。

### 2.2 移除/规避
- Telegram/Slack/Discord/IM 等复杂接入。
- 多模型供应商聚合复杂性（仅保留 OpenAI-compatible 内网网关）。
- 多租户/计费等企业内网一期无关能力。

---

## 3. 新增模块说明

```
nanobot/internal_orchestrator/
├── settings.py      # 环境变量配置
├── tools.py         # 工具注册与 mock 工具
├── llm.py           # 内网 LLM OpenAI-compatible 客户端
├── agent.py         # 简化编排引擎
├── api.py           # FastAPI + 简单 Web UI + API
└── main.py          # uvicorn 启动入口
```

### 3.1 编排引擎（`agent.py`）
- 系统提示词限定职责：仅用工具解决企业请求。
- 循环执行：
  1) 调用模型拿到 tool call 或直接回答。  
  2) 若有 tool call，解析参数并执行工具。  
  3) 将工具结果塞回上下文继续推理，直到得到最终回答。
- 通过 `max_loop_steps` 控制复杂请求兜底，避免死循环。

### 3.2 模型客户端（`llm.py`）
- 对接 `POST /chat/completions` OpenAI 协议。
- 若模型没走标准 `tool_calls`，尝试从 `content` 里修复出 `{name, arguments}`（弱模型兼容关键）。

### 3.3 工具注册与 mock（`tools.py`）
默认内置 3 类工具，代表常见企业数字服务：
- `query_data_statistics`：统计查询。
- `run_dl_prediction`：预测推理。
- `trigger_simulation`：仿真任务。

一期先 mock；二期替换 handler 内逻辑为真实 `httpx` / RPC 调用即可。

### 3.4 API 与入口（`api.py`, `main.py`）
- `POST /api/v1/orchestrate`：统一编排接口（系统与前端调用主入口）。
- `GET /`：超轻量页面，用于 PoC 快速演示。
- `GET /healthz`：健康检查。
- 启动命令：`nanobot-internal`（已加入 `pyproject.toml` 脚本）。

---

## 4. 企业内网部署建议

## 4.1 单机 PoC
1. 部署内网模型网关（vLLM/OpenAI-compatible）。
2. 设置环境变量：
   - `INTERNAL_ORCH_LLM_BASE_URL`
   - `INTERNAL_ORCH_LLM_API_KEY`
   - `INTERNAL_ORCH_LLM_MODEL`
3. 启动：`nanobot-internal`。

### 4.2 生产建议
- 编排层容器化，前置 Nginx/API Gateway 鉴权。
- 工具调用链加入审计日志（请求 ID、调用耗时、工具返回码）。
- 为工具服务定义超时和重试策略（尤其是仿真/长任务服务）。
- 将 `trace` 输出接入 ELK/Prometheus，形成可观测闭环。

---

## 5. 二次开发路线图

### 阶段 A（已实现）
- 最小编排内核 + 3 类 mock 工具 + Web/API 入口。
- 支持弱模型 tool-call 修复。

### 阶段 B（2~4 周）
- 对接真实 API：统一签名、鉴权、超时、重试、熔断。
- 新增工具筛选层（基于关键词 / 向量检索）以减少大模型工具选择负担。
- 增加会话态 memory（Redis）支持多轮业务任务。

### 阶段 C（1~2 个月）
- 接入 MCP server，把 Java/Go 遗留系统纳入统一工具域。
- 增加策略路由：根据任务类型选择不同内网模型。
- 引入审批/风控节点（高风险工具调用前人工确认）。

---

## 6. 安全与治理
- 内网 API 统一采用服务账号 + 最小权限。
- 工具参数白名单校验，防止 prompt 注入诱导越权调用。
- 对敏感数据输出做脱敏（手机号、身份证、财务主键）。
- 审计日志落盘至少包含：会话 ID、用户、工具名、参数摘要、结果摘要、耗时。

---

## 7. 验收标准（建议）
- 能稳定处理“统计查询 + 预测 + 仿真触发”三类请求。
- 在弱模型下，工具调用成功率 >= 90%（按内部测试集）。
- 关键接口 P95 响应 < 3s（不含仿真长任务）。
- 工具调用全链路可追踪（trace_id 级别）。

