"""Structured tool-call tracing for local observability and dashboards."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ToolTraceStore:
    """Append-only JSONL trace store."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (Path.home() / ".nanobot" / "logs" / "tool_trace.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: dict[str, Any]) -> None:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **event,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def tail(self, limit: int = 200) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
