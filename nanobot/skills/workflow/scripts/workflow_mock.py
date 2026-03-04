#!/usr/bin/env python3
"""Mock implementation of workflow functions for testing and development.

This provides a complete mock implementation that simulates real workflow behavior
including processing, interruptions, and success/failure scenarios.
"""

import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path


class MockWorkflowBackend:
    """Mock backend simulating workflow execution."""

    def __init__(self):
        self.storage_dir = Path.home() / ".nanobot" / "workspace" / "workflow_mock"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.workflows = {}

    def _get_workflow_path(self, run_id: str) -> Path:
        """Get storage path for a workflow."""
        return self.storage_dir / f"{run_id}.json"

    def _load_workflow(self, run_id: str) -> Dict[str, Any]:
        """Load workflow state from storage."""
        path = self._get_workflow_path(run_id)
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
        return None

    def _save_workflow(self, run_id: str, data: Dict[str, Any]) -> None:
        """Save workflow state to storage."""
        path = self._get_workflow_path(run_id)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def runworkflow(self, user_input: str) -> str:
        """Start a new workflow execution."""
        run_id = f"mock_{int(time.time() * 1000)}"

        # Simulate different scenarios based on input keywords
        input_lower = user_input.lower()

        # Determine workflow type
        if "compare" in input_lower or "vs" in input_lower:
            workflow_type = "comparison"
            nodes = ["start", "data_prep", "comparison", "end"]
        elif "outlier" in input_lower or "anomaly" in input_lower:
            workflow_type = "outlier_detection"
            nodes = ["start", "data_prep", "outlier_detect", "end"]
        elif "control" in input_lower or "impact" in input_lower:
            workflow_type = "controlled_analysis"
            nodes = ["start", "data_prep", "control_vars", "analysis", "end"]
        else:
            workflow_type = "general_analysis"
            nodes = ["start", "data_prep", "analysis", "end"]

        # Check if should interrupt (30% chance for demo)
        will_interrupt = random.random() < 0.3

        workflow_data = {
            "runId": run_id,
            "status": "processing" if not will_interrupt else "interrupted",
            "workflowType": workflow_type,
            "userInput": user_input,
            "nodes": {},
            "steps": nodes,
            "createdAt": datetime.now().isoformat(),
            "costMs": 0
        }

        # Initialize nodes
        for i, node_id in enumerate(nodes):
            workflow_data["nodes"][node_id] = {
                "input": user_input if i == 0 else {},
                "output": {},
                "status": "pending" if i > 0 else "processing",
                "costMs": 0,
                "nodeType": "start" if i == 0 else "end" if i == len(nodes) - 1 else "flow"
            }

        # Add interruption data if needed
        if will_interrupt:
            workflow_data["lastInterruptedNodeId"] = nodes[-2]  # Second to last node
            workflow_data["checkpointExpireTimestamp"] = int((datetime.now() + timedelta(hours=1)).timestamp() * 1000)
            workflow_data["msg"] = "请补充分析的时间范围（例如：Q1、Q2、或具体月份）"
            workflow_data["nodes"][nodes[-2]]["status"] = "interrupted"
        else:
            # Simulate successful completion
            workflow_data["output"] = self._generate_mock_output(workflow_type, user_input)
            workflow_data["status"] = "success"
            workflow_data["costMs"] = random.randint(1000, 5000)
            for node_id in nodes:
                workflow_data["nodes"][node_id]["status"] = "success"
                workflow_data["nodes"][node_id]["costMs"] = workflow_data["costMs"] // len(nodes)

        self._save_workflow(run_id, workflow_data)
        return run_id

    def getflowinfo(self, run_id: str) -> Dict[str, Any]:
        """Query workflow status."""
        workflow = self._load_workflow(run_id)

        if not workflow:
            return {
                "error": f"Workflow {run_id} not found",
                "status": "fail"
            }

        # Simulate processing -> success transition for demo
        if workflow["status"] == "processing" and random.random() < 0.4:
            workflow["status"] = "success"
            workflow["output"] = self._generate_mock_output(
                workflow.get("workflowType", "general_analysis"),
                workflow.get("userInput", "")
            )
            workflow["costMs"] = random.randint(1000, 5000)
            for node_id in workflow["nodes"]:
                workflow["nodes"][node_id]["status"] = "success"
            self._save_workflow(run_id, workflow)

        return workflow

    def resumeflow(self, user_input: str, run_id: str) -> None:
        """Resume an interrupted workflow."""
        workflow = self._load_workflow(run_id)

        if not workflow:
            raise ValueError(f"Workflow {run_id} not found")

        if workflow["status"] != "interrupted":
            raise ValueError(f"Workflow {run_id} is not interrupted (status: {workflow['status']})")

        # Resume and complete
        workflow["status"] = "success"
        workflow["userInput"] += f" | RESUMED: {user_input}"
        workflow["output"] = self._generate_mock_output(
            workflow.get("workflowType", "general_analysis"),
            workflow["userInput"]
        )
        workflow["costMs"] = workflow.get("costMs", 0) + random.randint(500, 2000)

        # Update interrupted node
        if "lastInterruptedNodeId" in workflow:
            node_id = workflow["lastInterruptedNodeId"]
            workflow["nodes"][node_id]["status"] = "success"

        # Mark all nodes as success
        for node_id in workflow["nodes"]:
            if workflow["nodes"][node_id]["status"] in ["interrupted", "pending"]:
                workflow["nodes"][node_id]["status"] = "success"

        # Remove interruption fields
        workflow.pop("lastInterruptedNodeId", None)
        workflow.pop("checkpointExpireTimestamp", None)
        workflow.pop("msg", None)

        self._save_workflow(run_id, workflow)

    def _generate_mock_output(self, workflow_type: str, user_input: str) -> Dict[str, Any]:
        """Generate mock output based on workflow type."""
        outputs = {
            "comparison": {
                "summary": f"基于对比分析，{user_input[:30]}... 显示Q2相比Q1增长15%，主要来自华东区域。",
                "details": {
                    "comparison": {
                        "period1": "Q1",
                        "period2": "Q2",
                        "change_rate": "+15%",
                        "regions": {
                            "华东": "+22%",
                            "华南": "+8%",
                            "华北": "+12%"
                        }
                    },
                    "outliers": [
                        {"region": "华东", "value": 1450000, "deviation": "3.2σ"}
                    ],
                    "controlled_analysis": {
                        "controlling_for": ["seasonality", "channel"],
                        "net_impact": "+18%"
                    },
                    "recommendation": [
                        "加大华东区域投入",
                        "调查华南区域增长缓慢原因"
                    ]
                }
            },
            "outlier_detection": {
                "summary": f"在{user_input[:30]}... 中识别出5个异常值，主要集中在A品类和B渠道。",
                "details": {
                    "comparison": {},
                    "outliers": [
                        {"id": 1, "value": 98000, "expected": 45000, "deviation": "4.1σ", "reason": "Promotional event"},
                        {"id": 2, "value": 12000, "expected": 38000, "deviation": "-3.5σ", "reason": "Stockout"},
                        {"id": 3, "value": 156000, "expected": 52000, "deviation": "4.8σ", "reason": "Bulk order"}
                    ],
                    "controlled_analysis": {},
                    "recommendation": [
                        "验证促销活动效果",
                        "补货B渠道",
                        "调查大宗订单异常"
                    ]
                }
            },
            "controlled_analysis": {
                "summary": f"通过控制变量分析，在{user_input[:30]}... 中发现价格调整对销量影响显著（-12%），但地区因素控制后影响为-8%。",
                "details": {
                    "comparison": {
                        "raw_correlation": "-12%",
                        "controlled_correlation": "-8%",
                        "controlled_variables": ["region", "season", "channel"]
                    },
                    "outliers": [],
                    "controlled_analysis": {
                        "method": "multiple_regression",
                        "r_squared": 0.87,
                        "significant_factors": ["price", "promotion", "season"]
                    },
                    "recommendation": [
                        "价格调整需谨慎，综合考虑地区因素",
                        "加强促销活动配合"
                    ]
                }
            },
            "general_analysis": {
                "summary": f"对 '{user_input[:50]}...' 的分析已完成。主要发现：数据呈现上升趋势，建议持续关注。",
                "details": {
                    "comparison": {
                        "trend": "上升",
                        "growth_rate": "+8.5%"
                    },
                    "outliers": [],
                    "controlled_analysis": {},
                    "recommendation": [
                        "继续监控趋势",
                        "深入分析驱动因素"
                    ]
                }
            }
        }

        return outputs.get(workflow_type, outputs["general_analysis"])


# Global instance
_backend = MockWorkflowBackend()


def runworkflow(user_input: str) -> str:
    """Start a new workflow execution."""
    return _backend.runworkflow(user_input)


def getflowinfo(run_id: str) -> Dict[str, Any]:
    """Query workflow status."""
    return _backend.getflowinfo(run_id)


def resumeflow(user_input: str, run_id: str) -> None:
    """Resume an interrupted workflow."""
    return _backend.resumeflow(user_input, run_id)


if __name__ == "__main__":
    # Quick test
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "run" and len(sys.argv) > 2:
            run_id = runworkflow(sys.argv[2])
            print(f"Started workflow: {run_id}")

        elif cmd == "info" and len(sys.argv) > 2:
            info = getflowinfo(sys.argv[2])
            print(json.dumps(info, indent=2, ensure_ascii=False))

        elif cmd == "resume" and len(sys.argv) > 3:
            resumeflow(sys.argv[2], sys.argv[3])
            print(f"Resumed workflow: {sys.argv[3]}")
        else:
            print("Usage: python workflow_mock.py [run|info|resume] [args...]")
    else:
        # Interactive demo
        print("=== Workflow Mock Demo ===\n")

        # Test 1: Run workflow
        print("1. Starting workflow...")
        run_id = runworkflow("Compare Q1 and Q2 sales")
        print(f"   Started: {run_id}\n")

        # Test 2: Get info
        print("2. Getting workflow info...")
        info = getflowinfo(run_id)
        print(f"   Status: {info['status']}")
        print(f"   Type: {info.get('workflowType', 'N/A')}\n")

        # Test 3: Format output
        if info["status"] == "success":
            print("3. Workflow completed!")
            print(f"   Summary: {info['output']['summary']}\n")
        elif info["status"] == "interrupted":
            print("3. Workflow interrupted!")
            print(f"   Message: {info['msg']}\n")
