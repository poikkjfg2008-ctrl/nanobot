# nanobot 最小化内网部署与自动化任务教程（中文样例）

> 目标：在**内网环境**里，使用你已有的本地大模型 API + 一个简单的 Markdown 读写服务，完成“读取业务知识库 Markdown、生成日报/项目介绍并写回服务器文件”的自动化流程。

## 1. 先做代码体检：当前仓库的可运行性与风险点

结合 `nanobot/intranet.py` 的实现，内网最小代理已经具备可运行闭环：

- `ToolRegistry`：工具注册与描述拼接。
- `TextMemory`：本地 append-only 文本记忆。
- `IntranetNanoAgent`：`<think>` + `<tool_call>` + `<tool_result>` 的工具调用循环。

建议重点关注下面两类问题（本次已处理）：

1. **LLM 响应结构异常导致崩溃**
   - 原实现直接读取 `body["choices"][0]["message"]["content"]`，若网关返回结构略有差异会抛 `KeyError/IndexError`。
   - 现在增加了结构校验并抛出更明确错误，便于排查网关协议不一致问题。

2. **关键采样参数不可配置**
   - 原实现 temperature 固定为 `0.1`，CLI 无法动态调整。
   - 现在新增 `temperature`、`max_tokens`、`timeout_s` 参数并暴露 CLI 开关，便于针对不同本地模型调优。

---

## 2. 最小化部署拓扑（可行方案）

推荐 3 个进程拆分，便于维护：

1. **本地 LLM API 网关**（你已有）
   - 需兼容 OpenAI Chat Completions 风格（`/v1/chat/completions`）。
2. **Markdown 文件服务（CentOS）**
   - 对目录 A 暴露“受控读写” HTTP API。
3. **nanobot 内网代理（本机/容器）**
   - 调用 LLM + 工具 API，完成日报/项目介绍生成，并可加定时任务。

---

## 3. nanobot 侧配置：接入本地大模型 API

### 3.1 启动方式

```bash
python -m nanobot.intranet \
  --base-url http://127.0.0.1:8000 \
  --api-key your-local-token \
  --model qwen2.5-14b-instruct \
  --temperature 0.2 \
  --timeout-s 60 \
  --max-tokens 2048 \
  --memory-file ./runtime/internal_session_memory.log
```

### 3.2 参数建议

- `--base-url`：本地/内网模型网关地址（不带 `/v1/chat/completions`）。
- `--api-key`：网关鉴权 token。
- `--model`：模型 ID（例如 `qwen2.5-14b-instruct`）。
- `--temperature`：
  - 报告类任务建议 `0.1~0.3`（稳定、可重复）；
  - 创意文案可提高到 `0.5~0.8`。
- `--max-tokens`：限制单次输出长度，防止输出过长。
- `--timeout-s`：内网慢服务建议调到 `60~120`。
- `--memory-file`：会话记忆文件路径。

---

## 4. 在 CentOS 部署“目录 A 的 Markdown 读写服务”（样例）

> 说明：这是一个最小可用样例，仅暴露特定根目录，并通过 token 鉴权 + 路径校验避免目录穿越。

### 4.1 目录准备

```bash
sudo mkdir -p /data/knowledgeA
sudo chown -R $USER:$USER /data/knowledgeA
```

### 4.2 安装依赖

```bash
python3 -m venv /opt/md-api/.venv
source /opt/md-api/.venv/bin/activate
pip install fastapi uvicorn
```

### 4.3 服务代码（`/opt/md-api/app.py`）

```python
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

ROOT = Path("/data/knowledgeA").resolve()
API_TOKEN = os.getenv("MD_API_TOKEN", "change-me")

app = FastAPI(title="markdown-rw-api")


class ReadReq(BaseModel):
    path: str


class WriteReq(BaseModel):
    path: str
    content: str


def _check_auth(token: str | None) -> None:
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


def _safe_path(rel_path: str) -> Path:
    target = (ROOT / rel_path).resolve()
    if not str(target).startswith(str(ROOT)):
        raise HTTPException(status_code=400, detail="invalid path")
    return target


@app.post("/read")
def read_file(req: ReadReq, x_api_token: str | None = Header(default=None)):
    _check_auth(x_api_token)
    target = _safe_path(req.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return {"path": req.path, "content": target.read_text(encoding="utf-8")}


@app.post("/write")
def write_file(req: WriteReq, x_api_token: str | None = Header(default=None)):
    _check_auth(x_api_token)
    target = _safe_path(req.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(req.content, encoding="utf-8")
    return {"ok": True, "path": req.path, "bytes": len(req.content.encode("utf-8"))}
```

### 4.4 启动服务

```bash
export MD_API_TOKEN='replace-with-strong-token'
source /opt/md-api/.venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 18081
```

### 4.5 快速验证

```bash
curl -s -X POST 'http://127.0.0.1:18081/write' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Token: replace-with-strong-token' \
  -d '{"path":"biz/knowledge.md","content":"# 业务知识\n- 产品A\n"}'

curl -s -X POST 'http://127.0.0.1:18081/read' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Token: replace-with-strong-token' \
  -d '{"path":"biz/knowledge.md"}'
```

---

## 5. 将 Markdown API 编排为 nanobot 工具（skill/task 思路）

### 5.1 工具封装示例（放在 `nanobot/intranet.py` 的 registry 中）

```python
import httpx

@registry.register("md_read", "读取知识库Markdown，参数: path")
def md_read(path: str) -> str:
    r = httpx.post(
        "http://centos-server:18081/read",
        headers={"X-API-Token": "replace-with-strong-token"},
        json={"path": path},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["content"]


@registry.register("md_write", "写入Markdown，参数: path, content")
def md_write(path: str, content: str) -> dict:
    r = httpx.post(
        "http://centos-server:18081/write",
        headers={"X-API-Token": "replace-with-strong-token"},
        json={"path": path, "content": content},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()
```

### 5.2 Skill 文档示例（给 agent 的行为规范）

你可以在 `~/.nanobot/skills/daily-md-writer/SKILL.md` 写入：

```md
---
name: daily-md-writer
description: 读取业务知识并生成日报/项目介绍，再写回Markdown。
---

# daily-md-writer

可用工具：
- md_read(path): 读取指定Markdown文件
- md_write(path, content): 写入Markdown文件

执行步骤：
1. 先用 md_read 读取 `biz/knowledge.md`。
2. 提炼关键事实，不得编造业务指标。
3. 生成 `reports/daily-YYYY-MM-DD.md`，结构如下：
   - 今日完成
   - 风险/阻塞
   - 明日计划
4. 用 md_write 写回结果。
```

---

## 6. 自动化：定时生成日报/项目介绍

可用两种方案：

1. **nanobot 内置 cron skill**（由 agent 自身管理）。
2. **系统级 crontab/systemd timer**（更可控，推荐生产）。

### 6.1 用 nanobot cron（概念示例）

```text
cron(action="add", message="每天18:30读取biz/knowledge.md并生成日报写入reports目录", cron_expr="30 18 * * 1-5", tz="Asia/Shanghai")
```

### 6.2 用 Linux crontab（推荐）

新增脚本 `/opt/nanobot/run_daily_report.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail

python -m nanobot.intranet \
  --base-url http://127.0.0.1:8000 \
  --api-key your-local-token \
  --model qwen2.5-14b-instruct \
  --temperature 0.2 \
  --timeout-s 60 <<'EOT'
请使用 md_read 读取 biz/knowledge.md，生成今天的中文日报，写入 reports/daily-$(date +%F).md。
EOT
```

然后配置 crontab：

```bash
crontab -e
# 每个工作日 18:30
30 18 * * 1-5 /opt/nanobot/run_daily_report.sh >> /var/log/nanobot_daily.log 2>&1
```

---

## 7. 一个“项目介绍文档”任务样例（同一套工具）

输入给 agent：

```text
读取 biz/knowledge.md 和 biz/milestones.md，整理为 project/project_intro.md。
要求：
1) 项目背景
2) 核心能力
3) 里程碑与成果
4) 已知风险与后续计划
最后调用 md_write 保存。
```

建议把“禁止编造、缺失信息标注 TODO”写进 skill，减少幻觉。

---

## 8. 生产建议（很重要）

- API token 放环境变量，不要硬编码到仓库。
- Markdown 服务建议加 Nginx + 内网白名单/IP 限制。
- 目录权限最小化：只开放目录 A，拒绝上级路径访问。
- 对 `md_write` 增加审计日志（谁在何时写了哪个文件）。
- 给报告任务增加“失败重试 + 告警（邮件/IM）”。

---

## 9. 排障清单

- 401：检查 `X-API-Token`。
- 404：检查读写相对路径是否存在。
- LLM 报错 `response format error`：网关返回格式与 OpenAI Chat Completions 不一致。
- 报告内容空泛：降低 `temperature`，并在 skill 中约束输出模板。


## 10. 针对“tool 参数正确但 API 未收到请求”的专项修复与调试

你反馈的现象（如 `</tool call`、`<im_start|>` 混杂、参数看起来正确但工具未触发）通常来自**弱结构化输出**：

- 工具标签不标准（`<tool call>` / 缺失 `</tool_call>`）。
- JSON 少括号、混入前后缀标记。
- 中间工具失败消息未被下一轮模型看到，导致模型反复错误调用。

本仓库已针对这类情况做了两层增强：

1. `internal_orchestrator/llm.py`：即使 tool 结果消息里缺失 `tool_name/name`，也会保留并转成兜底名称，避免失败上下文丢失。
2. `nanobot/intranet.py`：对 `<tool_call>` 提取与 payload 解析增加容错（兼容 `<tool call>`、缺失闭合标签、缺右花括号）。

### 10.1 建议的排障顺序（从外到内）

1) **先看 API 服务端日志**（确认是否收到 `/read` 或 `/write`）。
2) **打印模型原始输出**（确认是否生成了 `<tool_call>...</tool_call>`）。
3) **打印提取后的 payload**（确认 payload 进入 `_execute_tool_call` 前后的差异）。
4) **打印工具执行结果并回灌模型**（必须有 `<tool_result>...</tool_result>`）。
5) **核对下一轮请求是否包含上一步 tool_result**（否则模型无法纠错）。

### 10.2 建议临时日志点（生产可降级为 debug）

- `IntranetNanoAgent.chat`：记录 `content`、`tool_payload`、`tool_result`。
- `IntranetNanoAgent._execute_tool_call`：记录 `name`、`args`、异常栈。
- Markdown API 服务端：记录 `path`、调用来源 IP、认证结果。

### 10.3 快速自检脚本思路

可用三组输入回归：

1. 标准格式：`<tool_call>{"name":"md_read","args":{"path":"biz/knowledge.md"}}</tool_call>`
2. 错误闭合：`<tool_call>{...}</tool call`
3. 少右花括号：`{"name":"md_read","args":{"path":"biz/knowledge.md"}`

预期：1/2/3 都能进入工具执行；若 2/3 失败，检查容错逻辑是否被覆盖。
