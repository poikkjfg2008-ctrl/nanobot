# nanobot（内网优先版）

nanobot 是一个轻量级 Agent 框架，核心能力集中在三部分：

- `nanobot/agent`：通用 Agent 循环、上下文拼装、工具调用。
- `nanobot/skills`：可被模型动态注入的技能说明（`SKILL.md`）。
- `nanobot/internal_orchestrator`：面向企业内网服务编排的 FastAPI 网关。

本 README 基于当前仓库代码整理，重点面向「可落地、可运维、可二次开发」。

---

## 1. 当前代码能力总览

### 1.1 `nanobot/agent`（主 Agent）

- 以 `AgentLoop` 作为核心执行引擎：消息接入 → 上下文构建 → LLM 调用 → 工具执行 → 回写结果。
- 支持工具迭代、多轮处理、进度提示、工具调用 trace 记录。
- 运行入口主要是：
  - `nanobot agent`（CLI 对话）
  - `nanobot gateway`（多通道网关）

### 1.2 `nanobot/skills`（技能系统）

- 每个技能目录下通过 `SKILL.md` 定义：`name`、`description`、工作流约束。
- 运行时会发现技能元信息，在用户请求匹配场景下将技能内容注入上下文。
- 仓库内置技能包括：`github`、`weather`、`summarize`、`tmux`、`memory`、`cron`、`clawhub`、`skill-creator`、`daily-md-writer`。

### 1.3 `nanobot/internal_orchestrator`（内网编排服务）

- 提供独立的简化工具编排层（FastAPI）。
- 内置 3 个示例企业工具：统计查询、预测推理、仿真触发（默认 mock，可替换为真实 API）。
- 通过 `json-repair` 兼容弱模型输出不规范 JSON 的情况。
- CLI 启动命令：`nanobot-internal`。

---

## 2. 安装

```bash
git clone https://github.com/HKUDS/nanobot.git
cd nanobot
pip install -e .
```

要求：Python `>=3.11`。

---

## 3. 快速开始（主 Agent）

### 3.1 初始化

```bash
nanobot onboard
```

会创建：

- `~/.nanobot/config.json`
- `~/.nanobot/workspace` 及默认模板（`SOUL.md` / `USER.md` / `TOOLS.md` / `HEARTBEAT.md` 等）

### 3.2 配置本地模型（推荐内网）

`~/.nanobot/config.json` 示例（Ollama）：

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
      "model": "ollama/qwen2.5:14b"
    }
  }
}
```

`~/.nanobot/config.json` 示例（vLLM/OpenAI-Compatible）：

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

### 3.3 启动会话

```bash
nanobot agent
```

单轮模式：

```bash
nanobot agent -m "请总结今天待办并给出优先级"
```

---

## 4. 内网编排服务（`nanobot-internal`）

### 4.1 典型用途

- 把企业内部能力（统计、预测、仿真、报表）包装成工具。
- 用一个统一 API 接收业务问题并自动完成工具编排。
- 支持 Dashboard + trace，便于调试与审计。

### 4.2 环境变量

- `INTERNAL_ORCH_LLM_BACKEND`：`vllm` / `ollama`
- `INTERNAL_ORCH_LLM_BASE_URL`：模型地址
- `INTERNAL_ORCH_LLM_API_KEY`：鉴权 token
- `INTERNAL_ORCH_LLM_MODEL`：模型名
- `INTERNAL_ORCH_REQUEST_TIMEOUT_S`：请求超时
- `INTERNAL_ORCH_MAX_LOOP_STEPS`：最大编排轮数
- `INTERNAL_ORCH_TEMPERATURE`：采样温度

### 4.3 启动

```bash
nanobot-internal
```

默认监听 `0.0.0.0:8080`。

### 4.4 接口

- `GET /healthz`：健康检查
- `POST /api/v1/orchestrate`：编排主接口
- `GET /api/v1/traces`：读取工具调用链路
- `GET /`：内置调试页面

---

## 5. 文档导航（重点）

- 主 Agent 使用说明：[`USAGE_ZH.md`](USAGE_ZH.md)
- 内网部署教程（一步步）：[`INTRANET_DEPLOYMENT_ZH.md`](INTRANET_DEPLOYMENT_ZH.md)
- 技能机制说明：[`nanobot/skills/README.md`](nanobot/skills/README.md)
- 内网编排设计方案：[`nanobot/internal_orchestrator/PLAN.md`](nanobot/internal_orchestrator/PLAN.md)
- 内网编排最小化教程（原始版）：[`nanobot/internal_orchestrator/MINIMAL_DEPLOYMENT_ZH.md`](nanobot/internal_orchestrator/MINIMAL_DEPLOYMENT_ZH.md)

---

## 6. 开发与调试

运行测试：

```bash
pytest
```

查看最近工具调用 trace：

```bash
nanobot trace -n 100
```

