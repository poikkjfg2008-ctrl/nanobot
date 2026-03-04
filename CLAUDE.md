# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

nanobot is a lightweight AI agent framework designed for **intranet deployments** with three core components:

1. **nanobot/agent** - General agent loop, context building, and tool calling
2. **nanobot/skills** - Dynamically injectable skill descriptions (`SKILL.md`)
3. **nanobot/internal_orchestrator** - FastAPI gateway for enterprise intranet service orchestration

**Important**: This codebase is configured for **intranet-only deployments**. The provider registry (`nanobot/providers/registry.py`) only supports:
- **Ollama** - Local model server
- **vLLM** - OpenAI-compatible local gateways

Cloud providers (OpenAI, Anthropic, etc.) have been intentionally removed for intranet use.

## Development Commands

### Installation & Setup
```bash
# Install in development mode
pip install -e .

# Initialize workspace and config
nanobot onboard
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_commands.py

# Run with verbose output
pytest -v
```

### Code Quality
```bash
# Run linter
ruff check .

# Auto-fix linting issues
ruff check --fix .
```

### Running the Application

**Main Agent:**
```bash
# Interactive CLI session
nanobot agent

# Single-shot message
nanobot agent -m "your message here"

# Multi-channel gateway
nanobot gateway

# Web Dashboard (browser UI + API)
nanobot dashboard --host 0.0.0.0 --port 8090
# Or use: nanobot-dashboard
```

**Internal Orchestrator (Intranet):**
```bash
nanobot-internal
# Listens on 0.0.0.0:8080 by default
```

### Docker
```bash
# Build image
docker build -t nanobot .

# Run container
docker run -p 18790:18790 nanobot
```

## Architecture

### Agent Loop (`nanobot/agent/loop.py`)

The `AgentLoop` is the core processing engine:

1. Receives messages from the message bus (`InboundMessage`)
2. Builds context with history, memory, and skills
3. Calls the LLM via provider abstraction
4. Executes tool calls through the tool registry
5. Sends responses back (`OutboundMessage`)

Key concepts:
- **Session management**: Each conversation has a session with message history
- **Memory consolidation**: When session exceeds `memory_window`, background task consolidates old messages
- **Tool execution**: Tools are registered centrally and execute asynchronously
- **Progress callbacks**: Can emit intermediate updates during long operations
- **Trace storage**: All tool calls are recorded for debugging

### Tool System (`nanobot/agent/tools/`)

Tools are registered in a `ToolRegistry` and expose:
- `name`: Tool identifier
- `to_schema()`: OpenAI-compatible tool definition
- `execute(**params)`: Async execution
- `validate_params(params)`: Parameter validation

Available built-in tools:
- `shell`: Execute bash commands
- `web`: Web search and URL reading
- `filesystem`: File operations (read/write)
- `mcp`: Model Context Protocol server integration
- `message`: Send messages to channels
- `spawn`: Spawn subagents
- `cron`: Schedule jobs

### Skills System (`nanobot/skills/`)

Skills are **prompt-only** capabilities defined in markdown files:
- Each skill directory has a `SKILL.md` with YAML frontmatter
- Frontmatter defines `name` and `description`
- When user intent matches, the skill body is injected as task guidance
- Skills map steps to tool calls but don't contain code

To add a skill:
1. Create `nanobot/skills/<skill-name>/SKILL.md`
2. Define metadata and workflow instructions
3. Reference existing tools in the workflow

### Provider Abstraction (`nanobot/providers/`)

LLM providers implement the `LLMProvider` interface:
- `chat(messages, tools, model, ...) -> LLMResponse`
- Handle provider-specific API differences
- Support for reasoning content (DeepSeek-R1, Kimi)
- Empty content sanitization for robustness

Supported providers (intranet-only):
- **Ollama** - Local model server (default for `ollama/*` models)
- **LiteLLM** - Router for OpenAI-compatible endpoints (vLLM, local gateways)
  - Handles provider abstraction and API compatibility
  - Use `vllm/*` model prefixes for vLLM deployments

### Channel System (`nanobot/channels/`)

Channels provide multi-platform messaging:
- **BaseChannel**: Common interface for all platforms
- **ChannelManager**: Initializes and routes messages to enabled channels
- Supported: Telegram, WhatsApp, Discord, Feishu, Slack, QQ, DingTalk, Email

Channels convert platform-specific messages to/from `InboundMessage` and `OutboundMessage`.

### Internal Orchestrator (`nanobot/internal_orchestrator/`)

A **simplified** orchestration layer for enterprise intranets:
- **FastAPI** web service (`nanobot-internal` command)
- Tool orchestration loop optimized for internal services
- JSON-repair for weak model compatibility
- Mock tools (statistics, prediction, simulation) ready for real API integration
- Built-in web UI at `/` for testing and debugging
- Dashboard API endpoints for orchestration and trace inspection

Environment variables:
- `INTERNAL_ORCH_LLM_BACKEND`: `vllm` or `ollama`
- `INTERNAL_ORCH_LLM_BASE_URL`: Model endpoint
- `INTERNAL_ORCH_LLM_API_KEY`: Authentication token
- `INTERNAL_ORCH_LLM_MODEL`: Model name
- `INTERNAL_ORCH_MAX_LOOP_STEPS`: Max orchestration iterations (default: 10)
- `INTERNAL_ORCH_TEMPERATURE`: Sampling temperature
- `INTERNAL_ORCH_REQUEST_TIMEOUT_S`: Request timeout in seconds

### Dashboard (`nanobot/dashboard_api.py`, `nanobot/dashboard_main.py`)

Web-based interface for the main agent:
- Browser UI for chat interaction
- API endpoint: `POST /api/v1/chat` for programmatic access
- Trace inspection via `/api/v1/traces`
- Session management with configurable session IDs
- Provider initialization from config file
- Start with: `nanobot dashboard` or `nanobot-dashboard`

### Configuration (`~/.nanobot/config.json`)

Configuration structure:
```json
{
  "providers": {
    "ollama": {
      "apiBase": "http://127.0.0.1:11434",
      "apiKey": "ollama"
    },
    "vllm": {
      "apiBase": "http://127.0.0.1:8000/v1",
      "apiKey": "local"
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
  },
  "channels": {
    "telegram": {"enabled": true, "token": "..."},
    "whatsapp": {"enabled": false}
  }
}
```

## Key Design Patterns

### Message Flow
1. **Inbound**: Platform → Channel → Bus → AgentLoop
2. **Processing**: AgentLoop builds context → LLM → Tools → Results
3. **Outbound**: AgentLoop → Bus → Channel → Platform

### Context Building
Context is assembled from multiple sources (see `nanobot/agent/context.py`):
- **History**: Recent conversation turns from session
- **System prompts**: Persona and constraints from templates
- **Skills**: Relevant skill instructions based on intent
- **Tool definitions**: Available tools with schemas

### Error Handling
- Tool execution errors return error messages with `[Analyze the error above and try a different approach.]` hint
- Providers sanitize empty content to avoid 400 errors
- Sessions persist even if individual turns fail
- MCP connections have retry logic

## Important Implementation Details

### Memory Consolidation
- Runs in background when session exceeds `memory_window`
- Consolidates old messages into summaries
- Uses separate LLM call to compress history
- Prevents context from growing indefinitely
- Consolidated memories stored in `~/.nanobot/workspace/memory/`

### MCP Integration
- MCP servers configured in config file
- Connection established on first use
- Tools from MCP servers are registered in main tool registry
- Must call `await env.ensure_mcp_connected()` before processing
- Use for integrating external tools without modifying core codebase

### Session Keys
- Format: `{channel}:{chat_id}`
- Example: `telegram:123456789`, `cli:direct`, `dashboard:web`
- Used to isolate conversations and persist history
- Session files stored in `~/.nanobot/workspace/sessions/`

### Tool Progress Updates
- Long-running tools can emit progress via `on_progress` callback
- Used in CLI to show intermediate results
- Channels can stream progress to users

### Observability & Tracing
- All tool calls recorded to `~/.nanobot/logs/tool_trace.jsonl`
- View traces: `nanobot trace -n 100`
- Dashboard provides `/api/v1/traces` endpoint
- Internal orchestrator has separate trace storage

## Common Tasks

### Adding a New Tool
1. Create file in `nanobot/agent/tools/<tool_name>.py`
2. Inherit from `Tool` base class
3. Implement `execute()` and `validate_params()` methods
4. Register in `AgentOrchestrationEnvironment` (see `nanobot/application/orchestration/environment.py`)

Example:
```python
from nanobot.agent.tools.base import Tool

class MyTool(Tool):
    name = "my_tool"

    async def execute(self, **params):
        # Tool implementation
        return {"result": "success"}

    def validate_params(self, params):
        # Parameter validation
        return params
```

### Adding a New Channel
1. Create `nanobot/channels/<channel_name>.py`
2. Inherit from `BaseChannel`
3. Implement `start()` and `stop()` methods
4. Add configuration schema in `nanobot/config/schema.py`
5. Initialize in `ChannelManager._init_channels()`

### Testing Model Integration
```bash
# Test with local model (CLI)
nanobot agent -m "hello"

# Check tool traces
nanobot trace -n 20

# Test main agent dashboard
curl -X POST http://localhost:8090/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test message", "session_id": "test"}'

# Test internal orchestrator
curl -X POST http://localhost:8080/api/v1/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"query": "test request"}'
```

### Debugging Tool Calls
1. Enable debug logging: Set `LOG_LEVEL=DEBUG`
2. Check traces: `nanobot trace -n 50`
3. Inspect session files in `~/.nanobot/workspace/sessions/`
4. For main agent dashboard, check `/api/v1/traces` endpoint
5. For internal orchestrator, check `http://localhost:8080/api/v1/traces`
6. Check logs in `~/.nanobot/logs/tool_trace.jsonl`

## File Structure Notes

- **Templates**: `nanobot/templates/` - System prompts (SOUL.md, USER.md, TOOLS.md, HEARTBEAT.md)
- **Skills**: `nanobot/skills/` - Skill definitions with SKILL.md files
- **Tools**: `nanobot/agent/tools/` - Built-in tool implementations
- **Providers**: `nanobot/providers/` - LLM provider abstractions
- **Channels**: `nanobot/channels/` - Multi-platform messaging integrations
- **Internal Orchestrator**: `nanobot/internal_orchestrator/` - Enterprise orchestration layer
- **Dashboard**: `nanobot/dashboard_api.py`, `nanobot/dashboard_main.py` - Web interface
- **Bridge**: `bridge/` - Node.js WhatsApp bridge (separate project)
- **Tests**: `tests/` - Pytest-based test suite
- **Config**: Loaded from `~/.nanobot/config.json`
- **Workspace**: Default `~/.nanobot/workspace/` for sessions and memory
- **Logs**: `~/.nanobot/logs/` for tool traces and debugging

## Documentation

- **Main README**: `README.md` (Chinese, focused on intranet deployment)
- **Usage guide**: `USAGE_ZH.md` - Agent usage patterns and skill invocation
- **Intranet guide**: `INTRANET_GUIDE_ZH.md` - Intranet-specific deployment guidance
- **Tool integration**: `TOOL_INTEGRATION_PRACTICES_ZH.md` - Integrating external APIs
- **Skills documentation**: `nanobot/skills/README.md` - How skills work
- **Internal orchestrator plan**: `nanobot/internal_orchestrator/PLAN.md` - Design and architecture
- **Minimal deployment**: `nanobot/internal_orchestrator/MINIMAL_DEPLOYMENT_ZH.md` - Quick start guide

## Key Differences Between Components

### Main Agent vs Internal Orchestrator

**Main Agent** (`nanobot agent`, `nanobot dashboard`):
- Full-featured agent with extensive tool ecosystem
- Multi-channel support (Telegram, Discord, etc.)
- Skills system for dynamic capability injection
- Memory consolidation and long-running sessions
- Best for: Interactive assistants, complex multi-step tasks

**Internal Orchestrator** (`nanobot-internal`):
- Simplified orchestration layer for enterprise APIs
- Focused on business service integration (stats, prediction, simulation)
- JSON-repair for weak model compatibility
- Fixed tool set optimized for internal services
- Best for: Enterprise intranet service gateways, API orchestration

Both support:
- Local model backends (Ollama, vLLM)
- Tool call tracing and inspection
- Dashboard/web UI interfaces
- Configuration-based deployment
