# nanobot 内网离线部署与可观测性指南（Ollama / vLLM 专版）

> 本指南对应当前仓库的“内网化版本”：推理层仅保留 **Ollama** 与 **vLLM/OpenAI-Compatible 本地网关** 两种模式。

## 1. 目标与改造范围

### 1.1 推理后端
- ✅ 保留：`providers.ollama`、`providers.vllm`。
- ❌ 移除（不再参与匹配/路由）：OpenRouter、OpenAI、Anthropic、Gemini、DeepSeek、Moonshot、MiniMax、OAuth 等其它云侧模式。

### 1.2 运行形态
- `nanobot agent` / `nanobot gateway`：主 agent（带工具链）通过 LiteLLM 接本地 Ollama 或 vLLM。
- `nanobot-internal`：内网编排服务（FastAPI），支持 tool call 修复、追踪与 Dashboard。

---

## 2. 配置说明（仅内网）

配置文件：`~/.nanobot/config.json`

### 2.1 Ollama 示例
```json
{
  "providers": {
    "ollama": {
      "apiBase": "http://127.0.0.1:11434",
      "apiKey": "ollama"
    }
  },
  "agents": {
    "defaults": {
      "model": "ollama/qwen2.5:14b",
      "temperature": 0.1,
      "maxTokens": 4096,
      "maxToolIterations": 40,
      "memoryWindow": 100
    }
  }
}
```

### 2.2 vLLM 示例
```json
{
  "providers": {
    "vllm": {
      "apiBase": "http://127.0.0.1:8000/v1",
      "apiKey": "local"
    }
  },
  "agents": {
    "defaults": {
      "model": "vllm/Qwen2.5-32B-Instruct"
    }
  }
}
```

---

## 3. 工具调用链路日志在哪里看？

## 3.1 文件日志
统一写入：

- `~/.nanobot/logs/tool_trace.jsonl`

每行一条 JSON，字段包含：
- `ts`：UTC 时间
- `event`：`tool_call` / `final_answer`
- `session_key`、`channel`、`chat_id`、`sender_id`
- `tool`、`arguments`、`result`（工具执行结果摘要）

## 3.2 CLI 查看
```bash
nanobot trace -n 100
```

---

## 4. Dashboard 可视化监管（可用于调试）

当前已内置基础 Dashboard（`nanobot-internal` 启动后）：

- `GET /`：调试页面（左侧发起编排请求，右侧查看工具调用链）
- `GET /api/v1/traces?limit=200`：读取 trace JSONL
- `POST /api/v1/orchestrate`：编排入口

启动：
```bash
nanobot-internal
```

默认端口：`8080`。

---

## 5. 上下文设计（Context Design）

主 agent（`nanobot agent`）上下文由以下部分拼装：
1. 系统人格：`SOUL.md`
2. 用户画像：`USER.md`
3. 工具说明：`TOOLS.md`
4. 心跳任务：`HEARTBEAT.md`
5. 会话历史与记忆：`memory/HISTORY.md` 等

> 上述模板文件会在 `nanobot onboard` 时写入工作区，可直接编辑。

内网编排器（`nanobot-internal`）则使用固定系统提示词 `SYSTEM_PROMPT` + 轮次消息，并在每步中处理 tool calls。

---

## 6. 角色设定与提示词工程可改项

## 6.1 工作区模板（推荐）
- `SOUL.md`：角色人格、价值观、语气
- `USER.md`：用户信息与偏好
- `TOOLS.md`：工具使用约束
- `HEARTBEAT.md`：周期任务说明

## 6.2 内网编排器系统提示词
- 文件：`nanobot/internal_orchestrator/agent.py`
- 常量：`SYSTEM_PROMPT`
- 可扩展建议：
  - 强制“先工具后结论”的行为约束
  - 增加结果校验模板（例如置信度、数据来源）
  - 增加错误恢复策略（参数缺失时先追问）

## 6.3 弱模型工具调用修复
- 通过 `json_repair` 对 tool call 参数进行修复。
- 适用于工具调用 JSON 轻微畸形场景（括号、引号、逗号错误）。

---

## 7. 其他可调节参数（建议重点）

## 7.1 Agent 参数（`agents.defaults`）
- `model`：模型名（带 `ollama/` 或 `vllm/` 前缀）
- `temperature`：采样温度
- `maxTokens`：单轮输出长度
- `maxToolIterations`：最大工具迭代步数
- `memoryWindow`：纳入上下文的历史消息窗口

## 7.2 Tool 参数（`tools`）
- `exec.timeout`：命令执行超时
- `restrictToWorkspace`：是否限制工具只能访问工作区
- `web.search.maxResults`：检索结果上限

## 7.3 Internal Orchestrator 环境变量
- `INTERNAL_ORCH_LLM_BACKEND`：`vllm` 或 `ollama`
- `INTERNAL_ORCH_LLM_BASE_URL`：本地模型地址
- `INTERNAL_ORCH_LLM_API_KEY`：本地网关 token
- `INTERNAL_ORCH_LLM_MODEL`：模型名
- `INTERNAL_ORCH_REQUEST_TIMEOUT_S`：超时
- `INTERNAL_ORCH_MAX_LOOP_STEPS`：编排最大轮数
- `INTERNAL_ORCH_TEMPERATURE`：温度

---

## 8. 建议的企业内网落地策略

1. **优先 vLLM + 指令微调模型**：工具调用稳定性更高。  
2. **保留 Ollama 作为兜底/边缘节点**：开发调试成本低。  
3. **开启 trace 日志长期归档**：便于审计与复盘。  
4. **先收敛 SYSTEM_PROMPT 再扩展工具**：避免“工具太多导致调用漂移”。  
5. **按场景拆分子 agent**：报表、运营、研发助手各自维护最小工具集。  

