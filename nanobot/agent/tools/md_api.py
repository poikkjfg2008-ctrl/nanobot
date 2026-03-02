"""Markdown API tools for remote markdown file operations."""

import os
from typing import Any

import httpx

from nanobot.agent.tools.base import Tool

# Configuration
MD_API_BASE_URL = "http://0.0.0.0:18081"
# Get token from environment, with a fallback default
MD_API_TOKEN = os.getenv("MD_API_TOKEN") or "replace-with-strong-token"


class MDReadTool(Tool):
    """Tool to read markdown files via the md-api service."""

    def __init__(self):
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=MD_API_BASE_URL,
                headers={"X-API-Token": MD_API_TOKEN},
                timeout=30.0,
            )
        return self._client

    @property
    def name(self) -> str:
        return "md_read"

    @property
    def description(self) -> str:
        return "Read a markdown file from the remote knowledge base via md-api service."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The relative path to the markdown file (e.g., 'docs/readme.md')"
                }
            },
            "required": ["path"]
        }

    async def execute(self, path: str, **kwargs: Any) -> str:
        try:
            client = await self._get_client()
            response = await client.post("/read", json={"path": path})
            response.raise_for_status()
            data = response.json()
            return f"Successfully read {data['path']}:\n\n{data['content']}"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"Error: File not found: {path}"
            return f"Error: HTTP {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error reading markdown file: {str(e)}"

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()


class MDWriteTool(Tool):
    """Tool to write markdown files via the md-api service."""

    def __init__(self):
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=MD_API_BASE_URL,
                headers={"X-API-Token": MD_API_TOKEN},
                timeout=30.0,
            )
        return self._client

    @property
    def name(self) -> str:
        return "md_write"

    @property
    def description(self) -> str:
        return "Write content to a markdown file in the remote knowledge base via md-api service."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The relative path to the markdown file (e.g., 'reports/weekly.md')"
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
            client = await self._get_client()
            response = await client.post("/write", json={"path": path, "content": content})
            response.raise_for_status()
            data = response.json()
            return f"Successfully wrote {data['bytes']} bytes to {data['path']}"
        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error writing markdown file: {str(e)}"

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
