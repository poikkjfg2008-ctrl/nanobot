"""OpenAI/Ollama-compatible internal LLM client with tool-call repair."""

from __future__ import annotations

import json
from typing import Any

try:
    from json_repair import repair_json
except ImportError:  # pragma: no cover
    repair_json = None

from nanobot.internal_orchestrator.settings import InternalOrchestratorSettings


class InternalLLMClient:
    """Thin HTTP client for intranet model gateways (vLLM/Ollama)."""

    def __init__(self, settings: InternalOrchestratorSettings):
        self._settings = settings

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        if self._settings.llm_backend == "ollama":
            return await self._chat_ollama(messages=messages, tools=tools)
        return await self._chat_openai_compatible(messages=messages, tools=tools)

    async def _chat_openai_compatible(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": self._settings.llm_model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": self._settings.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        import httpx

        async with httpx.AsyncClient(timeout=self._settings.request_timeout_s) as client:
            response = await client.post(
                f"{self._settings.llm_base_url.rstrip('/')}/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()

        message = body["choices"][0]["message"]
        if message.get("tool_calls"):
            return message

        repaired = self._repair_tool_call_from_content(message.get("content"))
        if repaired:
            message["tool_calls"] = [repaired]
        return message

    async def _chat_ollama(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": self._settings.llm_model,
            "messages": self._to_ollama_messages(messages),
            "tools": tools,
            "stream": False,
            "options": {"temperature": self._settings.temperature},
        }

        import httpx

        async with httpx.AsyncClient(timeout=self._settings.request_timeout_s) as client:
            response = await client.post(
                f"{self._settings.llm_base_url.rstrip('/')}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        msg = body.get("message", {})
        content = msg.get("content", "")

        # Ollama native tool-call format: {"tool_calls": [{"function": {"name":..., "arguments": {...}}}]}
        raw_tool_calls = msg.get("tool_calls") or []
        if raw_tool_calls:
            tool_calls = []
            for idx, tc in enumerate(raw_tool_calls):
                fn = tc.get("function", {})
                arguments = fn.get("arguments", {})
                tool_calls.append(
                    {
                        "id": f"ollama-tool-call-{idx}",
                        "type": "function",
                        "function": {
                            "name": fn.get("name", ""),
                            "arguments": self._tool_arguments_to_json(arguments),
                        },
                    }
                )
            return {"content": content, "tool_calls": tool_calls}

        repaired = self._repair_tool_call_from_content(content)
        if repaired:
            return {"content": content, "tool_calls": [repaired]}
        return {"content": content, "tool_calls": []}

    @staticmethod
    def _tool_arguments_to_json(arguments: Any) -> str:
        if isinstance(arguments, str):
            return arguments
        if isinstance(arguments, dict):
            return json.dumps(arguments, ensure_ascii=False)
        return "{}"

    @staticmethod
    def _to_ollama_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert internally tracked OpenAI-style messages into Ollama-native payloads."""

        converted: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            if role == "tool":
                tool_name = InternalLLMClient._resolve_tool_name(msg)
                converted.append(
                    {
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": msg.get("content", ""),
                    }
                )
                continue

            if role == "assistant":
                converted_assistant = {"role": "assistant", "content": msg.get("content", "")}
                tool_calls = msg.get("tool_calls") or []
                normalized_tool_calls = []
                for idx, tc in enumerate(tool_calls):
                    fn = tc.get("function", {})
                    normalized_tool_calls.append(
                        {
                            "type": "function",
                            "function": {
                                "index": idx,
                                "name": fn.get("name", ""),
                                "arguments": InternalLLMClient._arguments_to_object(fn.get("arguments")),
                            },
                        }
                    )
                if normalized_tool_calls:
                    converted_assistant["tool_calls"] = normalized_tool_calls
                converted.append(converted_assistant)
                continue

            converted.append(msg)
        return converted

    @staticmethod
    def _arguments_to_object(arguments: Any) -> dict[str, Any]:
        if isinstance(arguments, dict):
            return arguments
        if not isinstance(arguments, str):
            return {}
        try:
            parsed = json.loads(repair_json(arguments) if repair_json else arguments)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
        return {}

    @staticmethod
    def _resolve_tool_name(message: dict[str, Any]) -> str:
        explicit_name = message.get("tool_name") or message.get("name")
        if isinstance(explicit_name, str) and explicit_name.strip():
            return explicit_name.strip()

        tool_call_id = message.get("tool_call_id")
        if isinstance(tool_call_id, str) and tool_call_id.strip():
            return f"unknown_tool_{tool_call_id.strip()}"

        return "unknown_tool"

    def _repair_tool_call_from_content(self, content: str | None) -> dict[str, Any] | None:
        if not content:
            return None
        try:
            repaired_text = repair_json(content) if repair_json else content
            repaired = json.loads(repaired_text)
        except Exception:
            return None

        if not isinstance(repaired, dict) or "name" not in repaired:
            return None
        arguments = repaired.get("arguments", {})
        if not isinstance(arguments, dict):
            return None

        return {
            "id": "repaired-tool-call-0",
            "type": "function",
            "function": {
                "name": repaired["name"],
                "arguments": json.dumps(arguments, ensure_ascii=False),
            },
        }
