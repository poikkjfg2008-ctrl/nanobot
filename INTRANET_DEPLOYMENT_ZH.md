# nanobot 内网部署教程（聚焦 `internal_orchestrator`）

本文是面向企业内网环境的可执行教程，基于当前 `nanobot/internal_orchestrator` 代码能力。

## 1. 目标架构

推荐最小部署拓扑：

1. **内网 LLM 网关**（vLLM 或 Ollama）
2. **nanobot internal orchestrator**（FastAPI 编排层）
3. **企业工具服务**（统计 / 预测 / 仿真 / 报表等 API）

说明：仓库默认工具是 mock；上线时把工具 handler 替换成真实内部服务调用即可。

---

## 2. 安装与启动

## 2.1 安装

```bash
git clone https://github.com/HKUDS/nanobot.git
cd nanobot
pip install -e .
```

## 2.2 配置环境变量

### vLLM 示例

```bash
export INTERNAL_ORCH_LLM_BACKEND=vllm
export INTERNAL_ORCH_LLM_BASE_URL=http://127.0.0.1:8000
export INTERNAL_ORCH_LLM_API_KEY=local-token
export INTERNAL_ORCH_LLM_MODEL=Qwen2.5-32B-Instruct
export INTERNAL_ORCH_REQUEST_TIMEOUT_S=45
export INTERNAL_ORCH_MAX_LOOP_STEPS=3
export INTERNAL_ORCH_TEMPERATURE=0.1
```

### Ollama 示例

```bash
export INTERNAL_ORCH_LLM_BACKEND=ollama
export INTERNAL_ORCH_LLM_BASE_URL=http://127.0.0.1:11434
export INTERNAL_ORCH_LLM_MODEL=qwen2.5:14b
```

## 2.3 启动服务

```bash
nanobot-internal
```

默认端口：`8080`。

---

## 3. API 验证

## 3.1 健康检查

```bash
curl -s http://127.0.0.1:8080/healthz
```

期望：`{"status":"ok"}`。

## 3.2 编排接口

```bash
curl -s http://127.0.0.1:8080/api/v1/orchestrate \
  -H 'Content-Type: application/json' \
  -d '{"query":"查询 ecommerce 今天 sales，并给出下周预测","session_id":"demo"}'
```

返回字段：

- `status`
- `session_id`
- `answer`
- `trace`（本次工具调用链）

## 3.3 调用链查看

```bash
curl -s 'http://127.0.0.1:8080/api/v1/traces?limit=200'
```

此外可打开浏览器访问 `http://127.0.0.1:8080/` 查看调试页面。

---

## 4. 工具替换（从 mock 到生产）

修改文件：`nanobot/internal_orchestrator/tools.py`

当前默认注册 3 个工具：

- `query_data_statistics`
- `run_dl_prediction`
- `trigger_simulation`

上线步骤：

1. 保留 `ToolSpec` + `ToolRegistry` 结构不变。
2. 将各 handler 改为调用真实 API（建议 `httpx`，设置超时/重试）。
3. 对参数做白名单校验。
4. 结果统一转成 JSON 字符串返回，保持编排层协议稳定。

---

## 5. 稳定性建议（弱模型场景）

- 使用指令遵循更好的模型，降低工具调用漂移。
- 保持 `INTERNAL_ORCH_MAX_LOOP_STEPS` 在 `3~5`，避免长链死循环。
- 保留 `json-repair` 兼容逻辑，减少非标准 JSON 导致的失败。
- 对每个工具设置明确、窄化的参数 schema。

---

## 6. 运维与审计

- 通过 `/api/v1/traces` 和本地 trace 文件观察调用链路。
- 在网关层增加鉴权（如内部 API Gateway / Nginx 认证）。
- 对高风险工具调用增加审批或人工确认。
- 记录会话 ID、工具名、参数摘要、耗时、返回状态。

