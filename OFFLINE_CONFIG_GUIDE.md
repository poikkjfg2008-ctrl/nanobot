# nanobot 离线部署配置指南

> 本文档详细说明如何在离线/内网环境中配置和调整 nanobot

## 目录

1. [环境准备](#环境准备)
2. [基础配置](#基础配置)
3. [高级配置](#高级配置)
4. [Ollama 集成](#ollama-集成)
5. [自定义工具](#自定义工具)
6. [故障排查](#故障排查)

---

## 环境准备

### 1. 系统要求

- **Python**: >= 3.11
- **操作系统**: Linux/macOS
- **内存**: 至少 8GB (推荐 16GB)
- **磁盘**: 至少 10GB 可用空间

### 2. Python 环境

```bash
# 创建虚拟环境
python3.11 -m venv /path/to/venv

# 激活虚拟环境
source /path/to/venv/bin/activate

# 安装 nanobot
cd /path/to/nanobot
pip install -e .
```

### 3. Ollama 安装

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# 启动 Ollama 服务
ollama serve

# 下载模型
ollama pull qwen3:14b
# 或
ollama pull qwen2.5:14b
```

### 4. 验证安装

```bash
# 检查 Python
python --version
# Python 3.11.x

# 检查 Ollama
curl http://localhost:11434/api/tags

# 初始化 nanobot
nanobot onboard
```

---

## 基础配置

### 配置文件位置

```
~/.nanobot/
├── config.json          # 主配置文件
└── workspace/           # 工作区
    ├── memory/          # 记忆存储
    ├── sessions/        # 会话历史
    └── skills/          # 自定义技能
```

### 最小化配置示例

```json
{
  "agents": {
    "defaults": {
      "model": "qwen3:14b",
      "temperature": 0.1
    }
  },
  "providers": {
    "ollama": {
      "apiBase": "http://localhost:11434",
      "apiKey": "ollama"
    }
  }
}
```

### 完整配置说明

```json
{
  // ========== Agent 配置 ==========
  "agents": {
    "defaults": {
      "workspace": "~/.nanobot/workspace",     // 工作区路径
      "model": "qwen3:14b",                    // 使用的模型
      "maxTokens": 8192,                       // 最大输出 token 数
      "temperature": 0.1,                      // 温度参数 (0.0-1.0)
      "maxToolIterations": 40,                 // 最大工具调用次数
      "memoryWindow": 100                      // 历史消息窗口大小
    }
  },

  // ========== Provider 配置 ==========
  "providers": {
    "ollama": {
      "apiBase": "http://172.24.16.1:11434",  // Ollama API 地址
      "apiKey": "ollama",                      // API 密钥（通常为 "ollama"）
      "extraHeaders": null                     // 额外的 HTTP 头
    },
    "vllm": {
      "apiBase": "http://localhost:8000/v1",  // vLLM API 地址
      "apiKey": "local"                        // API 密钥
    }
  },

  // ========== 工具配置 ==========
  "tools": {
    "exec": {
      "timeout": 60                            // 命令执行超时（秒）
    },
    "restrictToWorkspace": true,               // 限制工具只能访问工作区
    "web": {
      "search": {
        "apiKey": "",                          // 搜索 API 密钥
        "maxResults": 5                        // 最大搜索结果数
      }
    },
    "mcpServers": {}                           // MCP 服务器配置
  },

  // ========== Gateway 配置 ==========
  "gateway": {
    "host": "0.0.0.0",                         // 监听地址
    "port": 18790,                             // 监听端口
    "heartbeat": {
      "enabled": true,                         // 启用心跳
      "intervalS": 1800                        // 心跳间隔（秒）
    }
  },

  // ========== 通道配置 ==========
  "channels": {
    "sendProgress": true,                      // 发送进度更新
    "sendToolHints": false,                    // 发送工具提示
    "telegram": { ... },                       // Telegram 通道
    "email": { ... }                           // Email 通道
  }
}
```

---

## 高级配置

### 1. 模型选择

#### 支持的 Ollama 模型

| 模型 | 大小 | 推荐用途 | 工具调用 |
|------|------|----------|----------|
| qwen3:14b | ~9GB | 通用任务 | ✅ 支持 |
| qwen2.5:14b | ~9GB | 通用任务 | ✅ 支持 |
| qwen3:8b | ~5GB | 轻量级任务 | ✅ 支持 |
| llama3.2:3b | ~2GB | 快速响应 | ⚠️ 较弱 |

#### 模型切换

```bash
# 方法 1: 修改配置文件
vim ~/.nanobot/config.json
# "model": "qwen3:8b"

# 方法 2: 临时指定
nanobot agent -m "消息" --model qwen3:8b
```

### 2. 性能优化

#### 2.1 降低温度（更确定）

```json
{
  "agents": {
    "defaults": {
      "temperature": 0.0
    }
  }
}
```

#### 2.2 减少上下文窗口

```json
{
  "agents": {
    "defaults": {
      "memoryWindow": 50
    }
  }
}
```

#### 2.3 限制工具调用次数

```json
{
  "agents": {
    "defaults": {
      "maxToolIterations": 20
    }
  }
}
```

### 3. 安全设置

#### 3.1 启用工作区限制

```json
{
  "tools": {
    "restrictToWorkspace": true
  }
}
```

⚠️ **重要**：
- `true`: 只能访问 `~/.nanobot/workspace`
- `false`: 可以访问整个文件系统（安全风险）

#### 3.2 命令执行超时

```json
{
  "tools": {
    "exec": {
      "timeout": 30  // 30 秒后超时
    }
  }
}
```

### 4. 日志和监控

#### 查看工具调用日志

```bash
# 实时监控
tail -f ~/.nanobot/logs/tool_trace.jsonl

# 格式化查看
tail -20 ~/.nanobot/logs/tool_trace.jsonl | python3 -m json.tool
```

#### 日志字段说明

```json
{
  "ts": "2026-03-02T04:40:38.599940+00:00",  // 时间戳
  "event": "tool_call",                      // 事件类型
  "iteration": 1,                            // 迭代次数
  "tool": "read_file",                       // 工具名称
  "arguments": { ... },                      // 工具参数
  "result": "...",                           // 执行结果
  "channel": "cli",                          // 通道
  "chat_id": "direct",                       // 聊天 ID
  "session_key": "cli:direct",               // 会话键
  "sender_id": "user"                        // 发送者 ID
}
```

---

## Ollama 集成

### 1. 本地 Ollama

#### 配置

```json
{
  "providers": {
    "ollama": {
      "apiBase": "http://localhost:11434",
      "apiKey": "ollama"
    }
  },
  "agents": {
    "defaults": {
      "model": "qwen3:14b"
    }
  }
}
```

#### 验证

```bash
# 测试 Ollama API
curl http://localhost:11434/api/tags

# 测试 nanobot 连接
nanobot agent -m "你好"
```

### 2. 远程 Ollama

#### 配置

```json
{
  "providers": {
    "ollama": {
      "apiBase": "http://172.24.16.1:11434",
      "apiKey": "ollama"
    }
  }
}
```

#### 防火墙设置

```bash
# Ollama 服务器端（172.24.16.1）
# 设置环境变量允许远程访问
export OLLAMA_HOST=0.0.0.0:11434
ollama serve

# 或使用 systemd
sudo systemctl edit ollama
# 添加：
# [Service]
# Environment="OLLAMA_HOST=0.0.0.0:11434"
```

### 3. Ollama 性能调优

#### 模型量化选择

```bash
# 查看可用模型
ollama list

# 查看模型信息
ollama show qwen3:14b

# 重新下载不同量化版本
ollama pull qwen3:14b-q4_0  # Q4_0 量化
ollama pull qwen3:14b-q5_k_m  # Q5_K_M 量化
```

#### 内存限制

```bash
# 设置 Ollama 内存限制
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_NUM_GPU=1  # 使用 GPU 数量
```

### 4. 多模型配置

```json
{
  "agents": {
    "defaults": {
      "model": "qwen3:14b"
    },
    "tasks": {
      "quick": {
        "model": "qwen3:8b",
        "temperature": 0.0
      },
      "creative": {
        "model": "qwen3:14b",
        "temperature": 0.7
      }
    }
  }
}
```

---

## 自定义工具

### 1. 创建简单工具

#### 文件位置

```
nanobot/agent/tools/my_tool.py
```

#### 工具模板

```python
"""My custom tool."""

from typing import Any
from nanobot.agent.tools.base import Tool

class MyTool(Tool):
    """Description of my tool."""

    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Brief description of what this tool does"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Description of param1"
                }
            },
            "required": ["param1"]
        }

    async def execute(self, param1: str, **kwargs: Any) -> str:
        """Execute the tool logic."""
        try:
            # Your logic here
            result = f"Processed: {param1}"
            return result
        except Exception as e:
            return f"Error: {str(e)}"
```

### 2. 注册工具

#### 方法 1: 修改环境初始化

编辑 `nanobot/application/orchestration/environment.py`:

```python
def _register_default_tools(self) -> None:
    # ... existing tools ...

    # Register your tool
    from nanobot.agent.tools.my_tool import MyTool
    self.tools.register(MyTool())
```

#### 方法 2: 使用 MCP 服务器

配置 `config.json`:

```json
{
  "tools": {
    "mcpServers": {
      "my-server": {
        "command": "path/to/server",
        "args": ["--port", "3000"]
      }
    }
  }
}
```

### 3. MD-API 工具示例

#### 完整代码

```python
"""Markdown API tools for remote markdown file operations."""

import os
from typing import Any
import httpx
from nanobot.agent.tools.base import Tool

# Configuration
MD_API_BASE_URL = "http://0.0.0.0:18081"
MD_API_TOKEN = os.getenv("MD_API_TOKEN") or "replace-with-strong-token"

class MDReadTool(Tool):
    """Tool to read markdown files via the md-api service."""

    @property
    def name(self) -> str:
        return "md_read"

    @property
    def description(self) -> str:
        return "Read a markdown file from the remote knowledge base via md-api service"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The relative path to the markdown file"
                }
            },
            "required": ["path"]
        }

    async def execute(self, path: str, **kwargs: Any) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{MD_API_BASE_URL}/read",
                    headers={"X-API-Token": MD_API_TOKEN},
                    json={"path": path},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return f"Successfully read {data['path']}:\n\n{data['content']}"
        except Exception as e:
            return f"Error reading markdown file: {str(e)}"

class MDWriteTool(Tool):
    """Tool to write markdown files via the md-api service."""

    @property
    def name(self) -> str:
        return "md_write"

    @property
    def description(self) -> str:
        return "Write content to a markdown file in the remote knowledge base"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The relative path to the markdown file"
                },
                "content": {
                    "type": "string",
                    "description": "The markdown content to write"
                }
            },
            "required": ["path", "content"]
        }

    async def execute(self, path: str, content: str, **kwargs: Any) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{MD_API_BASE_URL}/write",
                    headers={"X-API-Token": MD_API_TOKEN},
                    json={"path": path, "content": content},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return f"Successfully wrote {data['bytes']} bytes to {data['path']}"
        except Exception as e:
            return f"Error writing markdown file: {str(e)}"
```

---

## 故障排查

### 问题 1: Ollama 连接失败

**错误信息**：
```
Error calling Ollama: Connection refused
```

**解决方法**：

```bash
# 1. 检查 Ollama 是否运行
ps aux | grep ollama

# 2. 检查端口
netstat -tlnp | grep 11434

# 3. 测试连接
curl http://localhost:11434/api/tags

# 4. 重启 Ollama
pkill ollama
ollama serve &
```

### 问题 2: LiteLLM 兼容性问题

**错误信息**：
```
Error calling LLM: Client error '400 Bad Request'
```

**解决方法**：

已修复！使用内置的 `OllamaProvider`：

1. 检查 `nanobot/providers/ollama_provider.py` 是否存在
2. 检查 `nanobot/cli/commands.py` 中的 `_make_provider` 函数

### 问题 3: 工具执行权限

**错误信息**：
```
Error: Permission denied
```

**解决方法**：

```bash
# 检查文件权限
ls -la ~/.nanobot/workspace

# 修改工作区权限
chmod 755 ~/.nanobot/workspace
chmod 644 ~/.nanobot/workspace/*.md
```

### 问题 4: 内存不足

**错误信息**：
```
Cannot allocate memory
```

**解决方法**：

```bash
# 1. 检查内存使用
free -h

# 2. 使用更小的模型
ollama pull qwen3:8b

# 3. 修改配置
vim ~/.nanobot/config.json
# "model": "qwen3:8b"
```

### 问题 5: 工具调用超时

**错误信息**：
```
Error: timeout
```

**解决方法**：

```json
{
  "tools": {
    "exec": {
      "timeout": 120  // 增加到 120 秒
    }
  }
}
```

### 问题 6: 会话过大

**症状**：
- 响应变慢
- 内存占用高

**解决方法**：

```bash
# 清除当前会话
echo "/new" | nanobot agent

# 或手动删除会话文件
rm ~/.nanobot/workspace/sessions/cli_direct.jsonl

# 减少历史窗口
vim ~/.nanobot/config.json
# "memoryWindow": 50
```

---

## 配置模板

### 场景 1: 开发环境

```json
{
  "agents": {
    "defaults": {
      "model": "qwen3:8b",
      "temperature": 0.2,
      "maxToolIterations": 20,
      "memoryWindow": 50
    }
  },
  "tools": {
    "exec": {
      "timeout": 30
    },
    "restrictToWorkspace": false
  }
}
```

### 场景 2: 生产环境

```json
{
  "agents": {
    "defaults": {
      "model": "qwen3:14b",
      "temperature": 0.1,
      "maxToolIterations": 40,
      "memoryWindow": 100
    }
  },
  "tools": {
    "exec": {
      "timeout": 60
    },
    "restrictToWorkspace": true
  },
  "gateway": {
    "host": "0.0.0.0",
    "port": 18790,
    "heartbeat": {
      "enabled": true,
      "intervalS": 1800
    }
  }
}
```

### 场景 3: 低资源环境

```json
{
  "agents": {
    "defaults": {
      "model": "qwen3:8b",
      "temperature": 0.0,
      "maxTokens": 4096,
      "maxToolIterations": 15,
      "memoryWindow": 30
    }
  },
  "tools": {
    "exec": {
      "timeout": 30
    }
  }
}
```

---

## 附录

### A. 环境变量

| 变量名 | 用途 | 默认值 |
|--------|------|--------|
| `NANOBOT_CONFIG` | 配置文件路径 | `~/.nanobot/config.json` |
| `NANOBOT_WORKSPACE` | 工作区路径 | `~/.nanobot/workspace` |
| `OLLAMA_HOST` | Ollama 地址 | `localhost:11434` |
| `MD_API_TOKEN` | MD-API 密钥 | - |

### B. 配置验证

```bash
# 验证 JSON 格式
python3 -m json.tool ~/.nanobot/config.json

# 检查配置文件语法
nanobot onboard

# 测试基本功能
nanobot agent -m "你好"
```

### C. 性能监控

```bash
# CPU 和内存使用
ps aux | grep nanobot

# 磁盘使用
du -sh ~/.nanobot

# 日志大小
du -sh ~/.nanobot/logs/
```

---

**文档版本**: 1.0
**最后更新**: 2026-03-02
**适用版本**: nanobot 0.1.4.post1
