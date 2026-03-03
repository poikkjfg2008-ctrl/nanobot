"""CLI bootstrap for running the nanobot agent dashboard web service."""

from __future__ import annotations

import uvicorn

from nanobot.dashboard_api import create_app


def main() -> None:
    uvicorn.run(create_app(), host="0.0.0.0", port=8090)


if __name__ == "__main__":
    main()
