#!/usr/bin/env python
"""Simple test script for nanobot agent."""

import asyncio
from pathlib import Path

from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.config.loader import load_config
from nanobot.config.schema import Config
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.session.manager import SessionManager


async def test_agent():
    """Test basic agent functionality."""

    # Load config
    config_path = Path.home() / ".nanobot" / "config.json"
    config = load_config(config_path)

    # Setup provider
    provider_config = config.providers.ollama
    provider = LiteLLMProvider(
        api_key=provider_config.api_key,
        api_base=provider_config.api_base,
        default_model=config.agents.defaults.model,
        provider_name="ollama"
    )

    # Setup workspace
    workspace = Path.home() / ".nanobot" / "workspace"

    # Setup message bus
    bus = MessageBus()

    # Setup session manager
    session_manager = SessionManager(workspace)

    # Create agent loop
    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=workspace,
        model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=config.agents.defaults.max_tool_iterations,
        memory_window=config.agents.defaults.memory_window,
        session_manager=session_manager,
        exec_config=config.tools.exec,
        cron_service=None,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        mcp_servers=config.tools.mcp_servers,
        channels_config=config.channels,
    )

    print("Testing agent with simple message...")

    # Test direct LLM call
    from loguru import logger
    logger.add("/tmp/nanobot_test.log", level="DEBUG")

    # Test simple message
    response = await agent.process_direct(
        "你好，请用一句话简单介绍一下你自己",
        session_key="test:basic"
    )

    print(f"\nResponse: '{response}'")
    print(f"Response length: {len(response)}")

    # Check trace
    traces = agent.trace_store.tail(limit=10)
    print(f"\nTraces: {len(traces)}")
    for t in traces:
        print(f"  - {t.get('event')}: {t.get('content', '')[:100]}")

    # Close agent
    await agent.close_mcp()
    agent.stop()


if __name__ == "__main__":
    asyncio.run(test_agent())
