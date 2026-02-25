"""OpenAI-compatible internal LLM client with tool-call repair."""

from __future__ import annotations

import json
from typing import Any

try:
    from json_repair import repair_json
except ImportError:  # pragma: no cover
    repair_json = None

from nanobot.internal_orchestrator.settings import InternalOrchestratorSettings


class InternalLLMClient:
    """Thin HTTP client for intranet model gateways compatible with OpenAI API."""

    def __init__(self, settings: InternalOrchestratorSettings):
        self._settings = settings

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": self._settings.llm_model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": self._settings.temperature,
        }
        headers = {"Authorization": f"Bearer {self._settings.llm_api_key}"}
        import httpx

        async with httpx.AsyncClient(timeout=self._settings.request_timeout_s) as client:
            response = await client.post(
                f"{self._settings.llm_base_url}/chat/completions",
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
