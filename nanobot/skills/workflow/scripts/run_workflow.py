#!/usr/bin/env python3
"""Start a new workflow execution.

Usage:
    python run_workflow.py "user input here"

Example:
    python run_workflow.py "Compare Q1 and Q2 sales by region"
"""

import sys
import json
from pathlib import Path

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# 导入工作流函数 - 支持Mock和真实实现切换
# 通过环境变量WORKFLOW_BACKEND控制: mock, http, cmd, import
import os
backend = os.environ.get("WORKFLOW_BACKEND", "mock")

if backend == "mock":
    from workflow_mock import runworkflow
elif backend in ("http", "cmd", "import"):
    from external_workflow import runworkflow
else:
    print(f"Warning: Unknown WORKFLOW_BACKEND '{backend}', using mock", file=sys.stderr)
    from workflow_mock import runworkflow


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_workflow.py '<user_input>'", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print('  python run_workflow.py "Compare Q1 and Q2 sales by region"', file=sys.stderr)
        sys.exit(1)

    user_input = " ".join(sys.argv[1:])

    try:
        run_id = runworkflow(user_input)
        print(run_id)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
