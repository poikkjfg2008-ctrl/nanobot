#!/usr/bin/env python3
"""External workflow implementation - 桥接到真实的workflow服务。

将此文件中的函数实现替换为你的真实后端调用逻辑。
"""

import os
import sys
from typing import Dict, Any
import json

# =============================================================================
# 配置区 - 根据你的实际环境修改
# =============================================================================

# 方式1: HTTP API (最常用)
WORKFLOW_API_BASE = os.environ.get("WORKFLOW_API_BASE", "http://localhost:5000")
WORKFLOW_API_TIMEOUT = int(os.environ.get("WORKFLOW_API_TIMEOUT", "30"))

# 方式2: 直接Python模块导入
# WORKFLOW_PYTHON_MODULE = os.environ.get("WORKFLOW_PYTHON_MODULE", "my_workflow_module")

# 方式3: 命令行调用
# WORKFLOW_CMD_PREFIX = os.environ.get("WORKFLOW_CMD_PREFIX", "/path/to/workflow-cli")


# =============================================================================
# HTTP API 实现 (推荐)
# =============================================================================

try:
    import requests

    def runworkflow_http(user_input: str) -> str:
        """通过HTTP API启动工作流."""
        try:
            response = requests.post(
                f"{WORKFLOW_API_BASE}/api/v1/workflow/run",
                json={"user_input": user_input},
                timeout=WORKFLOW_API_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()

            # 适配不同的响应格式
            if "run_id" in data:
                return data["run_id"]
            elif "runId" in data:
                return data["runId"]
            else:
                raise ValueError(f"Unexpected response format: {data}")

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to call workflow API: {e}")

    def getflowinfo_http(run_id: str) -> Dict[str, Any]:
        """通过HTTP API查询工作流状态."""
        try:
            response = requests.get(
                f"{WORKFLOW_API_BASE}/api/v1/workflow/{run_id}",
                timeout=WORKFLOW_API_TIMEOUT
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to get workflow info: {e}")

    def resumeflow_http(user_input: str, run_id: str) -> None:
        """通过HTTP API恢复工作流."""
        try:
            response = requests.post(
                f"{WORKFLOW_API_BASE}/api/v1/workflow/{run_id}/resume",
                json={"user_input": user_input},
                timeout=WORKFLOW_API_TIMEOUT
            )
            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to resume workflow: {e}")

    HTTP_AVAILABLE = True

except ImportError:
    # requests未安装，禁用HTTP方式
    HTTP_AVAILABLE = False
    print("Warning: requests library not installed. HTTP API mode disabled.", file=sys.stderr)


# =============================================================================
# 命令行实现 (备选)
# =============================================================================

import subprocess

def runworkflow_cmd(user_input: str) -> str:
    """通过命令行启动工作流."""
    try:
        cmd = [
            WORKFLOW_CMD_PREFIX,
            "run",
            user_input
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=WORKFLOW_API_TIMEOUT
        )

        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {result.stderr}")

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        raise RuntimeError("Workflow command timeout")
    except Exception as e:
        raise RuntimeError(f"Failed to run workflow command: {e}")


def getflowinfo_cmd(run_id: str) -> Dict[str, Any]:
    """通过命令行查询工作流状态."""
    try:
        cmd = [
            WORKFLOW_CMD_PREFIX,
            "info",
            run_id
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=WORKFLOW_API_TIMEOUT
        )

        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {result.stderr}")

        return json.loads(result.stdout)

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON response: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to get workflow info: {e}")


def resumeflow_cmd(user_input: str, run_id: str) -> None:
    """通过命令行恢复工作流."""
    try:
        cmd = [
            WORKFLOW_CMD_PREFIX,
            "resume",
            user_input,
            run_id
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=WORKFLOW_API_TIMEOUT
        )

        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        raise RuntimeError("Resume command timeout")
    except Exception as e:
        raise RuntimeError(f"Failed to resume workflow: {e}")


# =============================================================================
# 直接导入实现 (备选)
# =============================================================================

def runworkflow_import(user_input: str) -> str:
    """通过导入Python模块调用工作流."""
    try:
        module = __import__(WORKFLOW_PYTHON_MODULE)
        return module.runworkflow(user_input)
    except ImportError as e:
        raise RuntimeError(f"Failed to import workflow module: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to run workflow: {e}")


def getflowinfo_import(run_id: str) -> Dict[str, Any]:
    """通过导入Python模块查询工作流."""
    try:
        module = __import__(WORKFLOW_PYTHON_MODULE)
        return module.getflowinfo(run_id)
    except ImportError as e:
        raise RuntimeError(f"Failed to import workflow module: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to get workflow info: {e}")


def resumeflow_import(user_input: str, run_id: str) -> None:
    """通过导入Python模块恢复工作流."""
    try:
        module = __import__(WORKFLOW_PYTHON_MODULE)
        return module.resumeflow(user_input, run_id)
    except ImportError as e:
        raise RuntimeError(f"Failed to import workflow module: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to resume workflow: {e}")


# =============================================================================
# 统一接口 - 自动选择实现方式
# =============================================================================

# 读取环境变量选择实现方式
WORKFLOW_BACKEND = os.environ.get("WORKFLOW_BACKEND", "mock")  # mock, http, cmd, import

# 暴露给外部的函数
def runworkflow(user_input: str) -> str:
    """启动工作流 - 统一接口."""

    if WORKFLOW_BACKEND == "mock":
        # 使用Mock实现（用于测试）
        from workflow_mock import runworkflow as run_mock
        return run_mock(user_input)

    elif WORKFLOW_BACKEND == "http":
        # 使用HTTP API
        if not HTTP_AVAILABLE:
            raise RuntimeError("HTTP backend requested but requests library not available")
        return runworkflow_http(user_input)

    elif WORKFLOW_BACKEND == "cmd":
        # 使用命令行
        return runworkflow_cmd(user_input)

    elif WORKFLOW_BACKEND == "import":
        # 使用Python模块导入
        return runworkflow_import(user_input)

    else:
        raise ValueError(f"Unknown WORKFLOW_BACKEND: {WORKFLOW_BACKEND}")


def getflowinfo(run_id: str) -> Dict[str, Any]:
    """查询工作流状态 - 统一接口."""

    if WORKFLOW_BACKEND == "mock":
        from workflow_mock import getflowinfo as info_mock
        return info_mock(run_id)

    elif WORKFLOW_BACKEND == "http":
        if not HTTP_AVAILABLE:
            raise RuntimeError("HTTP backend requested but requests library not available")
        return getflowinfo_http(run_id)

    elif WORKFLOW_BACKEND == "cmd":
        return getflowinfo_cmd(run_id)

    elif WORKFLOW_BACKEND == "import":
        return getflowinfo_import(run_id)

    else:
        raise ValueError(f"Unknown WORKFLOW_BACKEND: {WORKFLOW_BACKEND}")


def resumeflow(user_input: str, run_id: str) -> None:
    """恢复工作流 - 统一接口."""

    if WORKFLOW_BACKEND == "mock":
        from workflow_mock import resumeflow as resume_mock
        return resume_mock(user_input, run_id)

    elif WORKFLOW_BACKEND == "http":
        if not HTTP_AVAILABLE:
            raise RuntimeError("HTTP backend requested but requests library not available")
        return resumeflow_http(user_input, run_id)

    elif WORKFLOW_BACKEND == "cmd":
        return resumeflow_cmd(user_input, run_id)

    elif WORKFLOW_BACKEND == "import":
        return resumeflow_import(user_input, run_id)

    else:
        raise ValueError(f"Unknown WORKFLOW_BACKEND: {WORKFLOW_BACKEND}")


# =============================================================================
# 主程序 - 用于测试
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test external workflow implementation")
    parser.add_argument("action", choices=["run", "info", "resume"], help="Action to perform")
    parser.add_argument("--input", help="User input for run/resume")
    parser.add_argument("--run-id", help="Workflow ID for info/resume")

    args = parser.parse_args()

    if args.action == "run":
        if not args.input:
            parser.error("--input required for 'run' action")
        run_id = runworkflow(args.input)
        print(f"Started: {run_id}")

    elif args.action == "info":
        if not args.run_id:
            parser.error("--run-id required for 'info' action")
        info = getflowinfo(args.run_id)
        print(json.dumps(info, indent=2, ensure_ascii=False))

    elif args.action == "resume":
        if not args.input or not args.run_id:
            parser.error("--input and --run-id required for 'resume' action")
        resumeflow(args.input, args.run_id)
        print(f"Resumed: {args.run_id}")
