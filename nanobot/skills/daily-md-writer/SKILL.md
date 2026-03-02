---
name: daily-md-writer
description: Read markdown knowledge files via md_read and write structured daily/weekly reports via md_write.
---

# daily-md-writer

## When to use
- 用户要求“读取业务 markdown 再写报告/周报”。
- 任务包含 `biz/*.md -> reports/*.md` 的归档流程。

## Required tools
- `md_read(path)`: 读取指定 Markdown 文件。
- `md_write(path, content)`: 写入 Markdown 文件。

## Workflow
1. 先调用 `md_read` 读取输入文档（至少 `biz/knowledge.md`）。
2. 提取事实，不编造数字；缺失信息明确标注 `TODO`。
3. 产出结构化文档后，再调用 `md_write` 写回目标文件。
4. 最终回复需说明：读取了哪些源文件、写入到哪个目标文件。

## Weekly report template
```markdown
# 周报（{{week_range}}）

## 本周完成
- ...

## 关键数据与事实
- ...

## 风险/阻塞
- ...

## 下周计划
- ...

## 待补充信息（TODO）
- ...
```

## Example instruction
- 请先读取 `biz/knowledge.md` 与 `biz/milestones.md`，生成中文周报并写入 `reports/weekly-2026-W10.md`。
