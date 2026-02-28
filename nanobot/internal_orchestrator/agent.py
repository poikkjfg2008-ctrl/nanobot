"""Minimal multi-step orchestrator for enterprise internal tools."""

from __future__ import annotations

import json
from typing import Any

try:
    from json_repair import repair_json
except ImportError:  # pragma: no cover
    repair_json = None

from nanobot.internal_orchestrator.llm import InternalLLMClient
from nanobot.internal_orchestrator.settings import InternalOrchestratorSettings
from nanobot.internal_orchestrator.tools import ToolRegistry, create_default_registry
from nanobot.observability.tool_trace import ToolTraceStore


SYSTEM_PROMPT = (
    "你是企业内部数字研发工具编排助手。"
    "必须优先使用可用工具完成统计分析、预测、仿真请求。"
    "当需要调用工具时，只输出标准 function call。"
)


class InternalToolAgent:
    """Simplified ReAct loop that only keeps tool orchestration essentials."""

    def __init__(
        self,
        llm_client: InternalLLMClient,
        registry: ToolRegistry,
        settings: InternalOrchestratorSettings,
    ) -> None:
        self._llm = llm_client
        self._registry = registry
        self._settings = settings
        self._trace_store = ToolTraceStore()

    @classmethod
    def from_defaults(cls) -> "InternalToolAgent":
        settings = InternalOrchestratorSettings.from_env()
        llm_client = InternalLLMClient(settings=settings)
        registry = create_default_registry()
        return cls(llm_client=llm_client, registry=registry, settings=settings)

    async def run(self, query: str, session_id: str = "default") -> dict[str, Any]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        trace: list[dict[str, Any]] = []

        for _ in range(self._settings.max_loop_steps):
            assistant_message = await self._llm.chat(messages=messages, tools=self._registry.schemas())
            messages.append({
                "role": "assistant",
                "content": assistant_message.get("content"),
                "tool_calls": assistant_message.get("tool_calls"),
            })

            tool_calls = assistant_message.get("tool_calls") or []
            if not tool_calls:
                return {
                    "status": "success",
                    "session_id": session_id,
                    "answer": assistant_message.get("content", ""),
                    "trace": trace,
                }

            for tool_call in tool_calls:
                function_obj = tool_call.get("function", {})
                name = function_obj.get("name", "")
                args = self._parse_arguments(function_obj.get("arguments", "{}"))
                result = await self._registry.execute(name, args)
                trace.append({"tool": name, "arguments": args, "result": result})
                self._trace_store.append(
                    {
                        "event": "tool_call",
                        "channel": "internal_orchestrator",
                        "session_key": session_id,
                        "tool": name,
                        "arguments": args,
                        "result": result,
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", "tool-call-0"),
                        "name": name,
                        "content": result,
                    }
                )

        return {
            "status": "error",
            "session_id": session_id,
            "answer": "系统调度超过最大步数，请简化问题或拆分请求。",
            "trace": trace,
        }

    @staticmethod
    def _parse_arguments(raw: str) -> dict[str, Any]:
        try:
            fixed = repair_json(raw) if repair_json else raw
            parsed = json.loads(fixed)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
        return {}
