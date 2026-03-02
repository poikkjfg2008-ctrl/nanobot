# nanobot 二次开发指南

> 本文档面向开发者，说明如何扩展和定制 nanobot

## 目录

1. [架构概览](#架构概览)
2. [开发环境搭建](#开发环境搭建)
3. [自定义工具开发](#自定义工具开发)
4. [自定义技能开发](#自定义技能开发)
5. [Provider 扩展](#provider-扩展)
6. [调试技巧](#调试技巧)
7. [最佳实践](#最佳实践)

---

## 架构概览

### 核心组件

```
nanobot/
├── agent/                 # Agent 核心
│   ├── loop.py           # 主循环
│   ├── context.py        # 上下文构建
│   ├── memory.py         # 记忆管理
│   ├── tools/            # 工具系统
│   │   ├── base.py       # 工具基类
│   │   ├── registry.py   # 工具注册
│   │   ├── filesystem.py # 文件操作
│   │   ├── shell.py      # 命令执行
│   │   └── ...
│   └── skills.py         # 技能加载器
├── providers/            # LLM Provider
│   ├── base.py           # Provider 接口
│   ├── litellm_provider.py
│   ├── ollama_provider.py # 自定义 Ollama Provider
│   └── registry.py       # Provider 注册
├── channels/             # 消息通道
├── config/               # 配置管理
└── cli/                  # 命令行接口
```

### 数据流

```
用户输入
  ↓
InboundMessage
  ↓
AgentLoop._process_message()
  ↓
ContextBuilder.build_messages()  ← 系统提示 + 技能 + 历史
  ↓
Provider.chat()  ← LLM 调用
  ↓
工具调用 (ToolRegistry.execute())
  ↓
工具结果回填
  ↓
循环直到完成
  ↓
OutboundMessage
  ↓
用户输出
```

---

## 开发环境搭建

### 1. 克隆和安装

```bash
# 克隆仓库
git clone https://github.com/HKUDS/nanobot.git
cd nanobot

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 开发模式安装
pip install -e ".[dev]"

# 验证安装
nanobot --version
nanobot agent -m "测试"
```

### 2. 开发工具

```bash
# 安装开发依赖
pip install pytest pytest-asyncio ruff

# 代码检查
ruff check .

# 代码格式化
ruff check --fix .

# 运行测试
pytest
```

### 3. IDE 配置

#### VSCode

创建 `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true
}
```

#### PyCharm

1. 设置 Python 解释器
2. 启用 Ruff 插件
3. 配置运行配置

---

## 自定义工具开发

### 1. 工具基类

所有工具继承自 `Tool` 基类：

```python
from nanobot.agent.tools.base import Tool

class MyTool(Tool):
    @property
    def name(self) -> str:
        """工具名称（用于调用）"""
        return "my_tool"

    @property
    def description(self) -> str:
        """工具描述（给 LLM 看）"""
        return "Brief description of what this tool does"

    @property
    def parameters(self) -> dict[str, Any]:
        """参数 schema（OpenAI 格式）"""
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Description of param1"
                },
                "param2": {
                    "type": "integer",
                    "description": "Description of param2"
                }
            },
            "required": ["param1"]
        }

    async def execute(self, param1: str, param2: int = 0, **kwargs) -> str:
        """执行工具逻辑"""
        try:
            # 你的逻辑
            result = f"Processed {param1} with {param2}"
            return result
        except Exception as e:
            return f"Error: {str(e)}"
```

### 2. 实战示例：数据库查询工具

```python
"""Database query tool for nanobot."""

import sqlite3
from pathlib import Path
from typing import Any
from nanobot.agent.tools.base import Tool

class DatabaseQueryTool(Tool):
    """Tool to query SQLite database."""

    def __init__(self, db_path: str = "~/data.db"):
        self.db_path = Path(db_path).expanduser().resolve()

    @property
    def name(self) -> str:
        return "db_query"

    @property
    def description(self) -> str:
        return "Execute SQL query on SQLite database and return results"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL SELECT query to execute"
                }
            },
            "required": ["query"]
        }

    async def execute(self, query: str, **kwargs: Any) -> str:
        """Execute SQL query."""
        try:
            # 安全检查：只允许 SELECT
            if not query.strip().upper().startswith("SELECT"):
                return "Error: Only SELECT queries are allowed"

            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 执行查询
            cursor.execute(query)
            rows = cursor.fetchall()

            # 获取列名
            columns = [desc[0] for desc in cursor.description]

            # 格式化结果
            result = [" | ".join(columns)]
            result.append("-" * len(result[0]))
            for row in rows:
                result.append(" | ".join(str(v) for v in row))

            conn.close()
            return "\n".join(result)

        except Exception as e:
            return f"Error executing query: {str(e)}"
```

### 3. 注册工具

#### 方法 1: 修改环境文件

编辑 `nanobot/application/orchestration/environment.py`:

```python
def _register_default_tools(self) -> None:
    # ... existing tools ...

    # 注册自定义工具
    from nanobot.agent.tools.my_tool import MyTool
    self.tools.register(MyTool())

    from nanobot.agent.tools.database import DatabaseQueryTool
    self.tools.register(DatabaseQueryTool())
```

#### 方法 2: 动态注册

```python
# 在运行时注册
from nanobot.application.orchestration.environment import AgentOrchestrationEnvironment

env = AgentOrchestrationEnvironment(...)
env.tools.register(MyTool())
```

### 4. 工具调试

```python
# 添加日志
from loguru import logger

async def execute(self, param1: str, **kwargs) -> str:
    logger.info(f"Executing {self.name} with param1={param1}")
    try:
        result = self._do_something(param1)
        logger.success(f"Tool {self.name} succeeded")
        return result
    except Exception as e:
        logger.error(f"Tool {self.name} failed: {e}")
        return f"Error: {str(e)}"
```

---

## 自定义技能开发

### 1. 技能结构

```
skills/my-skill/
└── SKILL.md
```

### 2. 技能模板

```markdown
---
name: my-skill
description: Brief description of what this skill does
always: false
metadata: {"nanobot":{"emoji":"🔧","requires":{"bins":[]}}}
---

# My Skill

## When to Use

Use this skill when the user asks for:
- Task 1
- Task 2
- Task 3

## Steps

1. Step one description
2. Step two description
3. Step three description

## Examples

### Example 1: Simple case

User: "help me do X"
Assistant: use tool1() then tool2()

### Example 2: Complex case

User: "help me do Y"
Assistant:
1. Use tool1() to check status
2. If condition A, use tool2()
3. Otherwise, use tool3()

## Notes

- Important note 1
- Important note 2

## Troubleshooting

If something goes wrong:
1. Check this
2. Try that
3. Contact admin
```

### 3. 实战示例：日志分析技能

```markdown
---
name: log-analyzer
description: Analyze log files and extract insights
metadata: {"nanobot":{"emoji":"📊","requires":{"bins":["grep","awk"]}}}
---

# Log Analyzer

## When to Use

Use this skill when the user asks to:
- Analyze log files
- Find errors or warnings
- Generate statistics from logs
- Monitor system health

## Workflow

### Step 1: Locate logs

Use `exec` tool to find log files:
```bash
find /var/log -name "*.log" -type f
```

### Step 2: Analyze patterns

Use grep to extract specific patterns:
```bash
grep -i "error" /var/log/app.log | tail -20
```

### Step 3: Generate report

Use `write_file` to save analysis results.

## Common Patterns

### Error counting

```bash
grep -c "ERROR" /var/log/app.log
```

### Time-based filtering

```bash
grep "2026-03-02" /var/log/app.log | grep "ERROR"
```

### Unique error types

```bash
grep "ERROR" /var/log/app.log | awk -F':' '{print $3}' | sort | uniq -c
```

## Examples

### Example 1: Find recent errors

User: "检查最近的错误"
Assistant:
1. Use exec: `grep -i "error" ~/.nanobot/logs/tool_trace.jsonl | tail -5`
2. Use read_file to view full details
3. Summarize findings

### Example 2: Generate error report

User: "生成错误报告"
Assistant:
1. Count errors: `grep -c "ERROR" /var/log/app.log`
2. Categorize errors: `grep "ERROR" /var/log/app.log | awk '{print $NF}' | sort | uniq -c`
3. Save report: `write_file("reports/error-report.md", content)`

## Notes

- Always check file permissions before reading
- Large log files should be sampled (tail/head)
- Consider log rotation when analyzing historical data
```

### 4. 技能测试

```bash
# 测试技能加载
nanobot agent -m "请读取 skills/my-skill/SKILL.md 文件"

# 测试技能功能
nanobot agent -m "使用 log-analyzer 技能分析最近的错误"

# 验证技能触发
grep -i "log" ~/.nanobot/logs/tool_trace.jsonl | tail -10
```

---

## Provider 扩展

### 1. Provider 接口

```python
from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest

class MyProvider(LLMProvider):
    """Custom LLM provider."""

    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        super().__init__(api_key, api_base)
        self.default_model = "my-model"

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send chat completion request."""
        # 1. 构建请求
        payload = self._build_payload(messages, tools, model, max_tokens, temperature)

        # 2. 调用 API
        response = await self._call_api(payload)

        # 3. 解析响应
        return self._parse_response(response)

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse API response into LLMResponse."""
        return LLMResponse(
            content=response.get("content"),
            tool_calls=self._extract_tool_calls(response),
            finish_reason=response.get("finish_reason", "stop"),
        )

    def get_default_model(self) -> str:
        return self.default_model
```

### 2. 注册 Provider

编辑 `nanobot/providers/registry.py`:

```python
PROVIDERS: tuple[ProviderSpec, ...] = (
    # ... existing providers ...

    ProviderSpec(
        name="myprovider",
        keywords=("myprovider", "my"),
        env_key="MYPROVIDER_API_KEY",
        display_name="My Provider",
        litellm_prefix="myprovider",
        skip_prefixes=("myprovider/",),
        is_local=True,
        default_api_base="http://localhost:8000",
    ),
)
```

### 3. CLI 集成

编辑 `nanobot/cli/commands.py`:

```python
def _make_provider(config: Config):
    # ... existing code ...

    # Add your provider
    if spec.name == "myprovider":
        from nanobot.providers.my_provider import MyProvider
        return MyProvider(
            api_key=p.api_key if p else None,
            api_base=config.get_api_base(model),
            default_model=model,
        )

    # ... rest of function ...
```

---

## 调试技巧

### 1. 启用详细日志

```python
from loguru import logger

# 添加到你的代码
logger.add("debug.log", level="TRACE")
```

### 2. 追踪工具调用

```bash
# 实时监控
tail -f ~/.nanobot/logs/tool_trace.jsonl | python3 -m json.tool

# 过滤特定工具
grep '"tool": "my_tool"' ~/.nanobot/logs/tool_trace.jsonl | tail -10
```

### 3. 测试单个工具

```python
# test_tool.py
import asyncio
from nanobot.agent.tools.my_tool import MyTool

async def test():
    tool = MyTool()
    result = await tool.execute(param1="test")
    print(f"Result: {result}")

asyncio.run(test())
```

### 4. 交互式调试

```python
# 在 Python REPL 中调试
from nanobot.application.orchestration.environment import AgentOrchestrationEnvironment
from nanobot.config.loader import load_config
from pathlib import Path

config = load_config(Path.home() / ".nanobot" / "config.json")
env = AgentOrchestrationEnvironment(...)

# 检查工具
print(env.tools.tool_names)
print(env.tools.get_definitions())
```

### 5. 单元测试

```python
# tests/test_my_tool.py
import pytest
from nanobot.agent.tools.my_tool import MyTool

@pytest.mark.asyncio
async def test_my_tool():
    tool = MyTool()
    result = await tool.execute(param1="test")
    assert "test" in result
    assert not result.startswith("Error")

@pytest.mark.asyncio
async def test_my_tool_error_handling():
    tool = MyTool()
    result = await tool.execute(param1="")
    assert "Error" in result
```

---

## 最佳实践

### 1. 工具开发

#### ✅ DO

- 使用清晰的工具名称（动词_名词）
- 提供详细的参数描述
- 添加完整的错误处理
- 使用类型提示
- 添加 docstring

#### ❌ DON'T

- 不要在工具中执行耗时操作（考虑使用 spawn）
- 不要硬编码路径（使用配置）
- 不要忽略异常
- 不要返回过大的结果（考虑截断）

### 2. 技能开发

#### ✅ DO

- 提供具体的示例
- 包含故障排查章节
- 使用清晰的步骤说明
- 考虑边界情况
- 保持技能专注（单一职责）

#### ❌ DON'T

- 不要写太长的技能文档
- 不要假设特定的工具可用
- 不要忽略错误处理
- 不要创建相互依赖的技能

### 3. 错误处理

#### 标准错误格式

```python
async def execute(self, **kwargs) -> str:
    try:
        result = self._do_something()
        return result
    except PermissionError as e:
        return f"Error: Permission denied - {str(e)}"
    except FileNotFoundError as e:
        return f"Error: File not found - {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
```

#### 错误恢复提示

```python
return f"Error: {str(e)}\n\n[Analyze the error above and try a different approach.]"
```

### 4. 性能优化

#### 异步操作

```python
# ❌ 不好：同步操作
def execute(self, **kwargs):
    result = subprocess.run(["ls", "-l"], capture_output=True)
    return result.stdout

# ✅ 好：异步操作
async def execute(self, **kwargs):
    proc = await asyncio.create_subprocess_exec(
        "ls", "-l",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode()
```

#### 结果截断

```python
# 截断过大的结果
max_chars = 500
if len(result) > max_chars:
    result = result[:max_chars] + "\n... (truncated)"
```

### 5. 安全考虑

#### 输入验证

```python
async def execute(self, path: str, **kwargs) -> str:
    # 验证路径
    resolved = Path(path).resolve()
    if not str(resolved).startswith(str(self.workspace)):
        return f"Error: Path {path} is outside allowed directory"

    # 验证命令
    if ";" in command or "|" in command:
        return f"Error: Command contains forbidden characters"
```

#### 权限控制

```python
async def execute(self, **kwargs) -> str:
    # 检查权限
    if not self._check_permission():
        return "Error: Insufficient permissions"

    # 执行操作
    return await self._do_operation()
```

---

## 常见开发任务

### 任务 1: 添加新的命令行选项

编辑 `nanobot/cli/commands.py`:

```python
@app.command()
def mycommand(
    message: str = typer.Argument(..., help="Message to send"),
    model: str = typer.Option(None, "--model", "-m", help="Model to use"),
):
    """My custom command."""
    config = load_config()
    provider = _make_provider(config)

    # 你的逻辑
    result = await agent.process_direct(message)

    console.print(result)
```

### 任务 2: 添加新的配置项

编辑 `nanobot/config/schema.py`:

```python
class MyConfig(BaseModel):
    """Custom configuration."""

    enabled: bool = False
    setting1: str = "default"
    setting2: int = 100

class Config(BaseModel):
    # ... existing fields ...

    my_config: MyConfig = Field(default_factory=MyConfig)
```

### 任务 3: 添加新的消息通道

1. 创建 `nanobot/channels/mychannel.py`
2. 继承 `BaseChannel`
3. 实现 `start()` 和 `stop()` 方法
4. 在 `ChannelManager` 中注册

```python
class MyChannel(BaseChannel):
    async def start(self):
        """启动通道"""
        while self._running:
            msg = await self._receive_message()
            await self.bus.publish_inbound(msg)

    async def stop(self):
        """停止通道"""
        self._running = False
```

---

## 附录

### A. 常用代码片段

#### 读取配置

```python
from nanobot.config.loader import load_config
from pathlib import Path

config = load_config(Path.home() / ".nanobot" / "config.json")
model = config.agents.defaults.model
```

#### 创建 Agent

```python
from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus

bus = MessageBus()
agent = AgentLoop(
    bus=bus,
    provider=provider,
    workspace=Path.home() / ".nanobot" / "workspace",
    model="qwen3:14b"
)
```

#### 使用工具注册表

```python
from nanobot.agent.tools.registry import ToolRegistry

registry = ToolRegistry()
registry.register(MyTool())

# 执行工具
result = await registry.execute("my_tool", {"param1": "value"})
```

### B. 调试命令

```bash
# 查看工具定义
nanobot agent -m "列出所有可用工具"

# 测试配置
python3 -m json.tool ~/.nanobot/config.json

# 检查技能
ls -la ~/.nanobot/workspace/skills/

# 查看会话
cat ~/.nanobot/workspace/sessions/cli_direct.jsonl | jq -c '.[] | select(.role == "user")'
```

### C. 有用的资源

- [nanobot GitHub](https://github.com/HKUDS/nanobot)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Typer Documentation](https://typer.tiangolo.com/)

---

**文档版本**: 1.0
**最后更新**: 2026-03-02
**适用版本**: nanobot 0.1.4.post1
