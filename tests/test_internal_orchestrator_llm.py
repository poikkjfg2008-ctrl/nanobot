import json

from nanobot.internal_orchestrator.llm import InternalLLMClient
from nanobot.internal_orchestrator.settings import InternalOrchestratorSettings


def test_to_ollama_messages_converts_tool_and_assistant_tool_calls():
    settings = InternalOrchestratorSettings()
    client = InternalLLMClient(settings=settings)

    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "query"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "query_data_statistics",
                        "arguments": '{"business_line":"ecommerce","metric":"sales","date":"2024-01-01"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call-1",
            "name": "query_data_statistics",
            "content": '{"value":"150000"}',
        },
    ]

    converted = client._to_ollama_messages(messages)

    assert converted[2]["tool_calls"][0]["type"] == "function"
    assert converted[2]["tool_calls"][0]["function"]["name"] == "query_data_statistics"
    assert converted[2]["tool_calls"][0]["function"]["arguments"] == {
        "business_line": "ecommerce",
        "metric": "sales",
        "date": "2024-01-01",
    }
    assert converted[3] == {
        "role": "tool",
        "tool_name": "query_data_statistics",
        "content": '{"value":"150000"}',
    }


def test_arguments_helpers_normalize_ollama_tool_arguments():
    assert InternalLLMClient._tool_arguments_to_json({"a": 1}) == '{"a": 1}'
    assert InternalLLMClient._tool_arguments_to_json('{"a":1}') == '{"a":1}'
    assert InternalLLMClient._tool_arguments_to_json(123) == "{}"

    parsed = InternalLLMClient._arguments_to_object('{"a": 1}')
    assert parsed == {"a": 1}


def test_repair_tool_call_from_content():
    client = InternalLLMClient(settings=InternalOrchestratorSettings())
    repaired = client._repair_tool_call_from_content(
        json.dumps({"name": "run_dl_prediction", "arguments": {"model_name": "m", "parameters": {}}})
    )
    assert repaired is not None
    assert repaired["function"]["name"] == "run_dl_prediction"
