"""CLI bootstrap for running the internal orchestrator web service."""

from __future__ import annotations

import uvicorn

from nanobot.internal_orchestrator.api import create_app


def main() -> None:
    uvicorn.run(create_app(), host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
