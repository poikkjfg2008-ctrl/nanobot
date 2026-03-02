# nanobot Skills

This directory contains built-in skills that extend nanobot's capabilities.

## Skill Format

Each skill is a directory containing a `SKILL.md` file with:
- YAML frontmatter (name, description, metadata)
- Markdown instructions for the agent

## How models use skills in this app

1. The runtime discovers skill directories and loads each `SKILL.md` metadata (`name` + `description`).
2. When a user request matches a skill's intent, the skill body is injected as task guidance.
3. The model follows the workflow constraints in that skill and maps steps to tool calls.
4. Tool outputs are fed back into the conversation; the model then continues until producing final answer.

> Practical tip: keep skills action-oriented (workflow + constraints + examples), not long theory docs.

## Skill usage tutorial (quick start)

### 1) Prepare tools
Ensure your runtime already registered the tools referenced in the skill (for example `md_read` and `md_write`).

### 2) Add or update a skill
Create a folder and `SKILL.md` under `nanobot/skills/<skill-name>/`.

### 3) Trigger by user prompt
Use explicit language in prompt, e.g. “请用 md_read 读取 ... 并用 md_write 写入 ...”。

### 4) Validate execution
Check:
- model actually emitted tool calls,
- tool backend received requests,
- tool result was returned to model,
- final answer references written target path.

## Example: weekly report using markdown tools

Skill: `daily-md-writer`

User prompt example:

```text
请读取 biz/knowledge.md 和 biz/milestones.md，生成本周中文周报并写入 reports/weekly-2026-W10.md。
必须先读再写，不要编造缺失数据。
```

Expected behavior:
- tool call 1: `md_read(path="biz/knowledge.md")`
- tool call 2: `md_read(path="biz/milestones.md")`
- tool call 3: `md_write(path="reports/weekly-2026-W10.md", content="...")`

## Attribution

These skills are adapted from [OpenClaw](https://github.com/openclaw/openclaw)'s skill system.
The skill format and metadata structure follow OpenClaw's conventions to maintain compatibility.

## Available Skills

| Skill | Description |
|-------|-------------|
| `github` | Interact with GitHub using the `gh` CLI |
| `weather` | Get weather info using wttr.in and Open-Meteo |
| `summarize` | Summarize URLs, files, and YouTube videos |
| `tmux` | Remote-control tmux sessions |
| `memory` | Manage persistent memory snippets |
| `cron` | Create and manage scheduled jobs |
| `clawhub` | Search and install skills from ClawHub registry |
| `skill-creator` | Create new skills |
| `daily-md-writer` | Read markdown knowledge and write daily/weekly reports |
