"""Markdown tools for local files or md-api service operations."""

import os
from pathlib import Path
from typing import Any

import httpx

from nanobot.agent.tools.base import Tool

DEFAULT_MD_API_BASE_URL = "http://0.0.0.0:18081"
DEFAULT_MD_API_TOKEN = "replace-with-strong-token"


def _resolve_local_base_dir(local_base_dir: str | None) -> Path:
    raw = local_base_dir or os.getenv("MD_API_LOCAL_BASE_DIR") or "~/.nanobot/workspace"
    return Path(raw).expanduser().resolve()


def _resolve_safe_local_path(path: str, local_base_dir: Path) -> Path:
    target = (local_base_dir / path).resolve()
    if local_base_dir not in target.parents and target != local_base_dir:
        raise PermissionError(f"Path '{path}' escapes base dir '{local_base_dir}'")
    return target


class MDReadTool(Tool):
    """Tool to read markdown files via the md-api service."""

    def __init__(self, *, mode: str | None = None, base_url: str | None = None, token: str | None = None,
                 local_base_dir: str | None = None):
        self._client = None
        self.mode = (mode or os.getenv("MD_API_MODE") or "http").lower()
        self.base_url = base_url or os.getenv("MD_API_BASE_URL") or DEFAULT_MD_API_BASE_URL
        self.token = token or os.getenv("MD_API_TOKEN") or DEFAULT_MD_API_TOKEN
        self.local_base_dir = _resolve_local_base_dir(local_base_dir)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"X-API-Token": self.token},
                timeout=30.0,
            )
        return self._client

    @property
    def name(self) -> str:
        return "md_read"

    @property
    def description(self) -> str:
        return "Read a markdown file from local storage or md-api service."

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
        if self.mode == "local":
            try:
                file_path = _resolve_safe_local_path(path, self.local_base_dir)
                if not file_path.exists():
                    return f"Error: File not found: {path}"
                content = file_path.read_text(encoding="utf-8")
                return f"Successfully read {path} from local store:\n\n{content}"
            except Exception as e:
                return f"Error reading local markdown file: {str(e)}"

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

    def __init__(self, *, mode: str | None = None, base_url: str | None = None, token: str | None = None,
                 local_base_dir: str | None = None):
        self._client = None
        self.mode = (mode or os.getenv("MD_API_MODE") or "http").lower()
        self.base_url = base_url or os.getenv("MD_API_BASE_URL") or DEFAULT_MD_API_BASE_URL
        self.token = token or os.getenv("MD_API_TOKEN") or DEFAULT_MD_API_TOKEN
        self.local_base_dir = _resolve_local_base_dir(local_base_dir)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"X-API-Token": self.token},
                timeout=30.0,
            )
        return self._client

    @property
    def name(self) -> str:
        return "md_write"

    @property
    def description(self) -> str:
        return "Write content to a markdown file in local storage or md-api service."

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
        if self.mode == "local":
            try:
                file_path = _resolve_safe_local_path(path, self.local_base_dir)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
                return f"Successfully wrote {len(content)} bytes to local file {path}"
            except Exception as e:
                return f"Error writing local markdown file: {str(e)}"

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
