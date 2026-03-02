"""Ollama provider using direct API calls."""

from __future__ import annotations

from typing import Any

import httpx
import json_repair

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class OllamaProvider(LLMProvider):
    """Direct Ollama API provider - bypasses LiteLLM for better compatibility."""

    def __init__(self, api_key: str = "ollama", api_base: str = "http://127.0.0.1:11434", default_model: str = "qwen2.5:14b"):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self._client = httpx.AsyncClient(
            base_url=api_base,
            headers={"Content-Type": "application/json"},
            timeout=120.0,
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send chat completion request to Ollama."""
        model = model or self.default_model

        # Build Ollama API request
        payload: dict[str, Any] = {
            "model": model,
            "messages": self._sanitize_messages(messages),
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            }
        }

        # Add tools if provided
        if tools:
            payload["tools"] = tools

        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return self._parse_response(data)
        except Exception as e:
            return LLMResponse(
                content=f"Error calling Ollama: {str(e)}",
                finish_reason="error",
            )

    def _sanitize_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove empty content and non-standard keys."""
        sanitized = []
        for msg in messages:
            content = msg.get("content")
            # Skip messages with empty/None content (but keep them if they have tool_calls)
            if not content and not msg.get("tool_calls"):
                continue

            clean_msg = {"role": msg["role"], "content": content}
            sanitized.append(clean_msg)
        return sanitized

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        """Parse Ollama API response."""
        message = data.get("message", {})
        content = message.get("content", "")

        # Parse tool calls if present
        tool_calls = []
        if "tool_calls" in message:
            for tc in message["tool_calls"]:
                tool_calls.append(
                    ToolCallRequest(
                        id=tc.get("id", ""),
                        name=tc["function"]["name"],
                        arguments=(
                            json_repair.loads(tc["function"]["arguments"])
                            if isinstance(tc["function"]["arguments"], str)
                            else tc["function"]["arguments"]
                        ),
                    )
                )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=data.get("done_reason", "stop"),
        )

    def get_default_model(self) -> str:
        return self.default_model

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
