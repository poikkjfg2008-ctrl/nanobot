#!/usr/bin/env python3
"""Query workflow status and details.

Usage:
    python get_workflow_info.py <run_id>

Example:
    python get_workflow_info.py mock_1234567890
"""

import sys
import json
from pathlib import Path

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# 导入工作流函数 - 支持Mock和真实实现切换
import os
backend = os.environ.get("WORKFLOW_BACKEND", "mock")

if backend == "mock":
    from workflow_mock import getflowinfo
elif backend in ("http", "cmd", "import"):
    from external_workflow import getflowinfo
else:
    print(f"Warning: Unknown WORKFLOW_BACKEND '{backend}', using mock", file=sys.stderr)
    from workflow_mock import getflowinfo


def main():
    if len(sys.argv) < 2:
        print("Usage: python get_workflow_info.py <run_id>", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print("  python get_workflow_info.py mock_1234567890", file=sys.stderr)
        sys.exit(1)

    run_id = sys.argv[1]

    try:
        info = getflowinfo(run_id)
        print(json.dumps(info, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
