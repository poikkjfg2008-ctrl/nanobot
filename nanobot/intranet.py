from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:
    import json_repair
except ImportError:  # pragma: no cover
    json_repair = None


ToolCallable = Callable[..., Any]


class ToolRegistry:
    """Register internal service wrappers as agent-callable tools."""

    def __init__(self) -> None:
        self.tools: dict[str, dict[str, Any]] = {}

    def register(self, name: str, desc: str) -> Callable[[ToolCallable], ToolCallable]:
        def decorator(func: ToolCallable) -> ToolCallable:
            self.tools[name] = {"func": func, "desc": desc}
            return func

        return decorator

    def get_tool_prompts(self) -> str:
        if not self.tools:
            return "- no tools registered"
        return "\n".join(f"- {name}: {meta['desc']}" for name, meta in self.tools.items())


class TextMemory:
    """Append-only plain text memory with keyword search."""

    def __init__(self, file_path: str = "internal_session_memory.log") -> None:
        self.file_path = Path(file_path)

    def append(self, role: str, content: str) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("a", encoding="utf-8") as memory_file:
            memory_file.write(f"[{role}] {content}\n")

    def search(self, keyword: str, limit: int = 3) -> str:
        if not self.file_path.exists():
            return ""
        matches: list[str] = []
        with self.file_path.open("r", encoding="utf-8") as memory_file:
            for line in memory_file:
                if keyword in line:
                    matches.append(line.rstrip())
        return "\n".join(matches[-limit:])


@dataclass
class IntranetAgentConfig:
    base_url: str
    api_key: str
    model: str = "internal-llm-model"
    timeout_s: float = 30.0


class IntranetNanoAgent:
    """Minimal robust loop for intranet deployment with weak-base models."""

    def __init__(self, config: IntranetAgentConfig, registry: ToolRegistry, memory: TextMemory) -> None:
        self.config = config
        self.registry = registry
        self.memory = memory
        self.messages: list[dict[str, str]] = [{"role": "system", "content": self._build_system_prompt()}]

    def _build_system_prompt(self) -> str:
        return f"""你是企业内部数字研发中心的数据助手。
你可以使用这些内网工具：
{self.registry.get_tool_prompts()}

当你需要调用工具时，必须严格输出：
<think>你的分析过程</think>
<tool_call>{{"name": "工具名", "args": {{"参数": "值"}}}}</tool_call>

拿到 <tool_result> 后请直接给出最终中文回答。
如果无需工具，直接回答。"""

    def _call_internal_llm(self) -> str:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": self.messages,
            "temperature": 0.1,
        }
        endpoint = f"{self.config.base_url.rstrip('/')}/v1/chat/completions"
        import httpx

        response = httpx.post(endpoint, json=payload, headers=headers, timeout=self.config.timeout_s)
        response.raise_for_status()
        body = response.json()
        return body["choices"][0]["message"]["content"]

    @staticmethod
    def _extract_tool_call(content: str) -> str | None:
        match = re.search(r"<tool_call>(.*?)</tool_call>", content, flags=re.DOTALL)
        return match.group(1).strip() if match else None

    def _execute_tool_call(self, payload: str) -> str:
        try:
            if json_repair is not None:
                call_data = json_repair.loads(payload)
            else:
                call_data = json.loads(payload)
        except Exception as exc:  # noqa: BLE001
            return f"工具调用 JSON 解析失败: {exc}"

        name = call_data.get("name")
        args = call_data.get("args", {})
        if name not in self.registry.tools:
            return f"工具未注册: {name}"

        try:
            result = self.registry.tools[name]["func"](**args)
        except Exception as exc:  # noqa: BLE001
            return f"工具执行失败: {exc}"

        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False)
        return str(result)

    def chat(self, user_input: str, step_limit: int = 5) -> str:
        self.messages.append({"role": "user", "content": user_input})
        self.memory.append("user", user_input)

        for _ in range(step_limit):
            content = self._call_internal_llm()
            self.messages.append({"role": "assistant", "content": content})
            tool_payload = self._extract_tool_call(content)

            if not tool_payload:
                self.memory.append("assistant", content)
                return content

            tool_result = self._execute_tool_call(tool_payload)
            observation = f"<tool_result>{tool_result}</tool_result>"
            self.messages.append({"role": "user", "content": observation})

        return "执行超时：工具调用轮次超过上限。"


def build_demo_registry() -> ToolRegistry:
    registry = ToolRegistry()

    @registry.register(
        "query_bi_report",
        "查询BI报表，参数: report_id(如 SALES_01), date(YYYY-MM-DD)",
    )
    def query_bi_report(report_id: str, date: str) -> dict[str, str]:
        return {
            "report_id": report_id,
            "date": date,
            "summary": "营业额500万，利润率12%",
        }

    return registry


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="nanobot intranet minimal agent")
    parser.add_argument("--base-url", required=True, help="Internal LLM gateway base url")
    parser.add_argument("--api-key", required=True, help="Internal LLM API key")
    parser.add_argument("--model", default="internal-llm-model", help="Model name")
    parser.add_argument("--memory-file", default="internal_session_memory.log", help="Memory file path")
    args = parser.parse_args()

    agent = IntranetNanoAgent(
        config=IntranetAgentConfig(base_url=args.base_url, api_key=args.api_key, model=args.model),
        registry=build_demo_registry(),
        memory=TextMemory(args.memory_file),
    )

    print("Intranet nanobot started. Input 'exit' to quit.")
    while True:
        user_input = input("you> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        print(f"bot> {agent.chat(user_input)}")


if __name__ == "__main__":
    run_cli()
