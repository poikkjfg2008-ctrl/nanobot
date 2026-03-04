#!/usr/bin/env python3
"""Resume an interrupted workflow with additional user input.

Usage:
    python resume_workflow.py "<user_input>" <run_id>

Example:
    python resume_workflow.py "Q1 2024" mock_1234567890
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
    from workflow_mock import resumeflow
elif backend in ("http", "cmd", "import"):
    from external_workflow import resumeflow
else:
    print(f"Warning: Unknown WORKFLOW_BACKEND '{backend}', using mock", file=sys.stderr)
    from workflow_mock import resumeflow


def main():
    if len(sys.argv) < 3:
        print("Usage: python resume_workflow.py '<user_input>' <run_id>", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print('  python resume_workflow.py "Q1 2024" mock_1234567890', file=sys.stderr)
        sys.exit(1)

    user_input = sys.argv[1]
    run_id = sys.argv[2]

    try:
        resumeflow(user_input, run_id)
        print(f"Workflow {run_id} resumed successfully")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
