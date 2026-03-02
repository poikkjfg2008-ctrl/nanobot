#!/usr/bin/env python
"""Detailed test script for nanobot agent."""

import asyncio
import json
from pathlib import Path

from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.config.loader import load_config
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
    print(f"Model: {config.agents.defaults.model}")

    # Test direct LLM call first
    messages = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Hello'}
    ]
    response = await provider.chat(messages=messages, model=config.agents.defaults.model)
    print(f"\nDirect LLM response: {response.content[:100]}")

    # Test with process_direct
    print("\n--- Testing process_direct ---")
    result = await agent.process_direct(
        "Hello, please introduce yourself in one sentence.",
        session_key="test:direct2"
    )

    print(f"\nResult type: {type(result)}")
    print(f"Result length: {len(result)}")
    print(f"Result repr: {repr(result[:200])}")
    print(f"\nFull result:\n{result}")

    # Check latest trace
    traces = agent.trace_store.tail(limit=5)
    print(f"\n\nLatest {len(traces)} traces:")
    for t in traces:
        content = t.get('content', '')
        print(f"  [{t.get('event')}] {content[:100] if content else '(empty)'}")

    # Close agent
    await agent.close_mcp()
    agent.stop()


if __name__ == "__main__":
    asyncio.run(test_agent())
