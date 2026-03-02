# nanobot 使用说明（基于当前代码）

本文档重点覆盖 `nanobot/agent` 与 `nanobot/skills` 的实际使用方式。

## 1. 运行入口

## 1.1 初始化

```bash
nanobot onboard
```

完成后会生成：

- `~/.nanobot/config.json`
- `~/.nanobot/workspace/`（包含默认模板和 memory 目录）

## 1.2 交互模式

```bash
nanobot agent
```

适合日常对话、工具调用、技能触发。

## 1.3 单次调用模式

```bash
nanobot agent -m "请根据 memory 生成本周计划"
```

适合脚本化调用或自动化任务。

## 1.4 网关模式

```bash
nanobot gateway
```

适合多通道统一接入（由 channel manager 管理）。

---

## 2. Agent 核心工作流（`nanobot/agent`）

`AgentLoop` 的执行逻辑可以概括为：

1. 接收消息（Bus）。
2. 组装上下文（系统模板 + 历史 + memory + 技能）。
3. 调用模型（provider.chat）。
4. 若返回 tool calls，则执行工具并回填结果。
5. 循环迭代直到得到最终回答或达到 `max_iterations`。

常用调优参数（`~/.nanobot/config.json`）：

- `agents.defaults.model`
- `agents.defaults.temperature`
- `agents.defaults.maxTokens`
- `agents.defaults.maxToolIterations`
- `agents.defaults.memoryWindow`

---

## 3. 技能系统（`nanobot/skills`）

## 3.1 技能格式

每个技能目录包含一个 `SKILL.md`，常见结构：

- YAML frontmatter：`name`、`description`、可选 `metadata`
- 正文：触发条件、步骤约束、命令示例

## 3.2 运行机制

1. 系统扫描技能目录，读取每个 `SKILL.md` 的元信息。
2. 当用户请求与技能意图匹配时，注入技能正文作为约束指令。
3. 模型按技能步骤选择并调用工具。

## 3.3 内置技能建议用法

- `daily-md-writer`：读业务 markdown 并生成日报/周报。
- `cron`：添加、查看、删除定时任务。
- `github`：通过 `gh` CLI 查询 PR / CI。
- `weather`：无 key 获取天气。
- `memory`：两层记忆结构（长期事实 + 历史事件）。
- `tmux`：远程控制交互式终端会话。

---

## 4. 常见操作示例

## 4.1 报告生成（结合技能）

```text
请先读取 biz/knowledge.md 和 biz/milestones.md，生成本周中文周报，写入 reports/weekly-2026-W10.md。
```

建议配合 `daily-md-writer` 技能。

## 4.2 查看工具调用轨迹

```bash
nanobot trace -n 100
```

日志用于排查：

- 是否发起了工具调用
- 入参与返回是否符合预期
- 会话中每一步调用链路是否完整

---

## 5. 推荐内网配置基线

- 优先使用 `ollama` 或 `vllm` 本地推理地址。
- `temperature` 从 `0.1` 起步（更稳定）。
- 开启并定期检查 `trace` 日志。
- 对高风险工具启用工作区限制（`restrictToWorkspace`）并最小权限运行。

