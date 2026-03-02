"""Minimal tool registry and mock enterprise tool implementations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


@dataclass(slots=True)
class ToolSpec:
    """Tool metadata used for LLM function-calling schema."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def as_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Simple in-memory tool registry for intranet service orchestration."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.as_openai_tool() for tool in self._tools.values()]

    async def execute(self, name: str, args: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if not tool:
            return json.dumps({"status": "error", "message": f"tool not found: {name}"}, ensure_ascii=False)
        return await tool.handler(args)


async def query_data_statistics(args: dict[str, Any]) -> str:
    business_line = args.get("business_line", "")
    metric = args.get("metric", "")
    date = args.get("date", "")
    mock_db = {
        "ecommerce": {"sales": "150000", "dau": "12000"},
        "gaming": {"sales": "80000", "dau": "45000"},
    }
    value = mock_db.get(business_line, {}).get(metric, "无数据")
    return json.dumps(
        {
            "status": "success",
            "source": "mock-data-warehouse",
            "business_line": business_line,
            "metric": metric,
            "date": date,
            "value": value,
        },
        ensure_ascii=False,
    )


async def run_dl_prediction(args: dict[str, Any]) -> str:
    model_name = args.get("model_name", "unknown")
    parameters = args.get("parameters", {})
    return json.dumps(
        {
            "status": "success",
            "source": "mock-dl-service",
            "model_name": model_name,
            "parameters": parameters,
            "prediction": "next_week_sales:+15%",
            "confidence": 0.89,
        },
        ensure_ascii=False,
    )


async def trigger_simulation(args: dict[str, Any]) -> str:
    sim_env = args.get("sim_env", "default")
    steps = args.get("steps", 100)
    return json.dumps(
        {
            "status": "running",
            "source": "mock-simulation-service",
            "job_id": "SIM-9982",
            "sim_env": sim_env,
            "steps": steps,
            "message": "仿真任务已启动",
        },
        ensure_ascii=False,
    )


def create_default_registry() -> ToolRegistry:
    """Build default registry with three representative enterprise tools."""

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="query_data_statistics",
            description="查询业务线统计指标，如销售额、DAU。",
            parameters={
                "type": "object",
                "properties": {
                    "business_line": {"type": "string"},
                    "metric": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["business_line", "metric", "date"],
            },
            handler=query_data_statistics,
        )
    )
    registry.register(
        ToolSpec(
            name="run_dl_prediction",
            description="调用内部深度学习推理服务并返回预测结果。",
            parameters={
                "type": "object",
                "properties": {
                    "model_name": {"type": "string"},
                    "parameters": {"type": "object"},
                },
                "required": ["model_name", "parameters"],
            },
            handler=run_dl_prediction,
        )
    )
    registry.register(
        ToolSpec(
            name="trigger_simulation",
            description="调用内部仿真服务并返回任务号。",
            parameters={
                "type": "object",
                "properties": {
                    "sim_env": {"type": "string"},
                    "steps": {"type": "integer", "minimum": 1},
                },
                "required": ["sim_env", "steps"],
            },
            handler=trigger_simulation,
        )
    )
    return registry
