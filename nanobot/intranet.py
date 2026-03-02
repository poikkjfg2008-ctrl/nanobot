from __future__ import annotations

import argparse
import json
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
    temperature: float = 0.1
    max_tokens: int | None = None


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
            "temperature": self.config.temperature,
        }
        if self.config.max_tokens is not None:
            payload["max_tokens"] = self.config.max_tokens
        endpoint = f"{self.config.base_url.rstrip('/')}/v1/chat/completions"
        import httpx

        response = httpx.post(endpoint, json=payload, headers=headers, timeout=self.config.timeout_s)
        response.raise_for_status()
        body = response.json()
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Internal LLM response format error: {body}") from exc

    @staticmethod
    def _extract_tool_call(content: str) -> str | None:
        opening_tags = ["<tool_call>", "<tool call>"]
        closing_tags = ["</tool_call>", "</tool call>"]

        start = -1
        start_len = 0
        for tag in opening_tags:
            idx = content.find(tag)
            if idx != -1 and (start == -1 or idx < start):
                start = idx
                start_len = len(tag)

        if start == -1:
            return None

        end = -1
        for tag in closing_tags:
            idx = content.find(tag, start + start_len)
            if idx != -1 and (end == -1 or idx < end):
                end = idx

        if end != -1:
            return content[start + start_len : end].strip()

        # 容错：若缺失闭合标签，尝试读取到文本末尾。
        return content[start + start_len :].strip()


    @staticmethod
    def _parse_tool_payload(payload: str) -> dict[str, Any] | None:
        candidates = [payload]

        loose_candidate = payload.strip()
        if loose_candidate and not loose_candidate.startswith("{"):
            start = loose_candidate.find("{")
            if start != -1:
                loose_candidate = loose_candidate[start:]
            candidates.append(loose_candidate)

        if payload.count("{") > payload.count("}"):
            candidates.append(payload + "}" * (payload.count("{") - payload.count("}")))

        for candidate in candidates:
            try:
                if json_repair is not None:
                    parsed = json_repair.loads(candidate)
                else:
                    parsed = json.loads(candidate)
            except Exception:
                continue
            if isinstance(parsed, dict):
                return parsed
        return None

    def _execute_tool_call(self, payload: str) -> str:
        call_data = self._parse_tool_payload(payload)
        if not isinstance(call_data, dict):
            return "工具调用 JSON 解析失败: payload 不是对象"

        name = call_data.get("name")
        args = call_data.get("args")
        if not isinstance(args, dict):
            args = {}
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
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--timeout-s", type=float, default=30.0, help="HTTP timeout in seconds")
    parser.add_argument("--max-tokens", type=int, default=None, help="Optional max_tokens for responses")
    args = parser.parse_args()

    agent = IntranetNanoAgent(
        config=IntranetAgentConfig(
            base_url=args.base_url,
            api_key=args.api_key,
            model=args.model,
            timeout_s=args.timeout_s,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        ),
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
