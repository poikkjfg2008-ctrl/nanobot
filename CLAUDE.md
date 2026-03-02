# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

nanobot is a lightweight AI agent framework with three core components:

1. **nanobot/agent** - General agent loop, context building, and tool calling
2. **nanobot/skills** - Dynamically injectable skill descriptions (`SKILL.md`)
3. **nanobot/internal_orchestrator** - FastAPI gateway for enterprise intranet service orchestration

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

Supported providers:
- **LiteLLM** (default): Multi-provider router (OpenAI, Anthropic, etc.)
- **OpenAI Codex**: OpenAI-compatible endpoints (vLLM, Ollama, local models)

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

Environment variables:
- `INTERNAL_ORCH_LLM_BACKEND`: `vllm` or `ollama`
- `INTERNAL_ORCH_LLM_BASE_URL`: Model endpoint
- `INTERNAL_ORCH_LLM_MODEL`: Model name
- `INTERNAL_ORCH_MAX_LOOP_STEPS`: Max orchestration iterations (default: 10)

### Configuration (`~/.nanobot/config.json`)

Configuration structure:
```json
{
  "providers": {
    "ollama": {"apiBase": "...", "apiKey": "..."},
    "openai": {"apiKey": "..."}
  },
  "agents": {
    "defaults": {
      "model": "ollama/qwen2.5:14b",
      "temperature": 0.1,
      "max_tokens": 4096
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

### MCP Integration
- MCP servers configured in config file
- Connection established on first use
- Tools from MCP servers are registered in main tool registry
- Must call `await env.ensure_mcp_connected()` before processing

### Session Keys
- Format: `{channel}:{chat_id}`
- Example: `telegram:123456789`, `cli:direct`
- Used to isolate conversations and persist history

### Tool Progress Updates
- Long-running tools can emit progress via `on_progress` callback
- Used in CLI to show intermediate results
- Channels can stream progress to users

## Common Tasks

### Adding a New Tool
1. Create file in `nanobot/agent/tools/<tool_name>.py`
2. Inherit from `Tool` base class
3. Implement `execute()` and `validate_params()`
4. Register in `AgentOrchestrationEnvironment` (see `nanobot/application/orchestration/environment.py`)

### Adding a New Channel
1. Create `nanobot/channels/<channel_name>.py`
2. Inherit from `BaseChannel`
3. Implement `start()` and `stop()` methods
4. Add configuration schema in `nanobot/config/schema.py`
5. Initialize in `ChannelManager._init_channels()`

### Testing Model Integration
```bash
# Test with local model
nanobot agent -m "hello"

# Check tool traces
nanobot trace -n 20

# Test internal orchestrator
curl -X POST http://localhost:8080/api/v1/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"query": "test request"}'
```

### Debugging Tool Calls
1. Enable debug logging: Set `LOG_LEVEL=DEBUG`
2. Check traces: `nanobot trace -n 50`
3. Inspect session files in `~/.nanobot/workspace/sessions/`
4. For orchestrator, check `/api/v1/traces` endpoint

## File Structure Notes

- **Templates**: `nanobot/templates/` - System prompts (SOUL.md, USER.md, TOOLS.md)
- **Bridge**: `bridge/` - Node.js WhatsApp bridge (separate project)
- **Tests**: `tests/` - Pytest-based test suite
- **Config**: Loaded from `~/.nanobot/config.json`
- **Workspace**: Default `~/.nanobot/workspace/` for sessions and memory

## Documentation

- Main README: `README.md` (Chinese, focused on intranet deployment)
- Usage guide: `USAGE_ZH.md`
- Intranet deployment: `INTRANET_DEPLOYMENT_ZH.md`
- Skills documentation: `nanobot/skills/README.md`
- Internal orchestrator plan: `nanobot/internal_orchestrator/PLAN.md`
