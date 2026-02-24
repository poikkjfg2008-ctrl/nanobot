import importlib

from nanobot.intranet import IntranetAgentConfig, IntranetNanoAgent, TextMemory, ToolRegistry


def test_text_memory_append_and_search(tmp_path):
    memory = TextMemory(str(tmp_path / "memory.log"))
    memory.append("user", "hello")
    memory.append("assistant", "world")
    memory.append("user", "hello again")

    result = memory.search("hello")
    assert "[user] hello" in result
    assert "[user] hello again" in result


def test_tool_call_execute():
    registry = ToolRegistry()

    @registry.register("add", "add two integers")
    def add(a: int, b: int) -> int:
        return a + b

    agent = IntranetNanoAgent(
        IntranetAgentConfig(base_url="http://localhost", api_key="test"),
        registry=registry,
        memory=TextMemory(),
    )

    payload = '{"name": "add", "args": {"a": 1, "b": 2}}'
    if importlib.util.find_spec("json_repair"):
        payload = '{name: "add", args: {a: 1, b: 2}}'

    result = agent._execute_tool_call(payload)
    assert result == "3"
