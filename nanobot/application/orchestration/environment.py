"""Application-layer orchestration environment.

Encapsulates composition of:
- skill-aware context building
- runtime tool registry
- MCP lifecycle (lazy connect/close)

This keeps AgentLoop focused on conversation control flow.
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from pathlib import Path

from loguru import logger

from nanobot.agent.context import ContextBuilder
from nanobot.agent.subagent import SubagentManager
from nanobot.agent.tools.cron import CronTool
from nanobot.agent.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from nanobot.agent.tools.md_api import MDReadTool, MDWriteTool
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.agent.tools.web import WebFetchTool, WebSearchTool
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider


class AgentOrchestrationEnvironment:
    """Build and host the runtime dependencies required by AgentLoop."""

    def __init__(
        self,
        *,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        brave_api_key: str | None,
        exec_config,
        cron_service,
        restrict_to_workspace: bool,
        mcp_servers: dict | None,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace
        self.mcp_servers = mcp_servers or {}

        self.context = ContextBuilder(workspace)
        self.tools = ToolRegistry()
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            brave_api_key=brave_api_key,
            exec_config=exec_config,
            restrict_to_workspace=restrict_to_workspace,
        )

        self._mcp_stack: AsyncExitStack | None = None
        self._mcp_connected = False
        self._mcp_connecting = False

        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the default toolchain for this environment."""
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        for cls in (ReadFileTool, WriteFileTool, EditFileTool, ListDirTool):
            self.tools.register(cls(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(ExecTool(
            working_dir=str(self.workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.restrict_to_workspace,
        ))
        self.tools.register(WebSearchTool(api_key=self.brave_api_key))
        self.tools.register(WebFetchTool())
        self.tools.register(MessageTool(send_callback=self.bus.publish_outbound))
        self.tools.register(SpawnTool(manager=self.subagents))
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))
        # Register md-api tools
        self.tools.register(MDReadTool())
        self.tools.register(MDWriteTool())

    async def ensure_mcp_connected(self) -> None:
        """Connect to configured MCP servers once (lazy, retry-on-failure)."""
        if self._mcp_connected or self._mcp_connecting or not self.mcp_servers:
            return

        self._mcp_connecting = True
        from nanobot.agent.tools.mcp import connect_mcp_servers

        try:
            self._mcp_stack = AsyncExitStack()
            await self._mcp_stack.__aenter__()
            await connect_mcp_servers(self.mcp_servers, self.tools, self._mcp_stack)
            self._mcp_connected = True
        except Exception as exc:  # pragma: no cover - depends on external MCP infra
            logger.error("Failed to connect MCP servers (will retry next message): {}", exc)
            if self._mcp_stack:
                try:
                    await self._mcp_stack.aclose()
                except Exception:
                    pass
                self._mcp_stack = None
        finally:
            self._mcp_connecting = False

    async def close(self) -> None:
        """Close managed resources (currently MCP sessions)."""
        if self._mcp_stack:
            try:
                await self._mcp_stack.aclose()
            except (RuntimeError, BaseExceptionGroup):
                pass
            self._mcp_stack = None
            self._mcp_connected = False

