"""Tests for Topic 08: LangChain & Tool Calling."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from langchain_core.messages import AIMessage, ToolMessage

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from tool_agent import (
    ToolCallingAgent,
    calculate,
    code_sandbox_evaluator,
    get_system_status,
    system_metrics,
    web_search_mock,
)


def test_calculate_tool():
    res1 = calculate.invoke({"expression": "12 * 12"})
    assert res1 == "144"

    res2 = calculate.invoke({"expression": "100 / 4"})
    assert res2 == "25.0"

    res3 = calculate.invoke({"expression": "10 / 0"})
    assert "error" in res3.lower() or "division" in res3.lower()


def test_system_status_tool():
    status = get_system_status.invoke({})
    assert "Status: Operational" in status
    assert "Python:" in status


def test_web_search_mock_tool():
    res = web_search_mock.invoke({"query": "What is new in Python?"})
    assert "Search results" in res
    assert "Python" in res

    # Unmatched query returns fallback search info
    res_fallback = web_search_mock.invoke({"query": "Quantum Computing 101"})
    assert "Search results for 'Quantum Computing 101'" in res_fallback


def test_code_sandbox_evaluator_tool():
    # Safe expression
    res_expr = code_sandbox_evaluator.invoke({"code": "[x * 2 for x in range(3)]"})
    assert "[0, 2, 4]" in res_expr

    # Multi-line statement with print
    res_stmt = code_sandbox_evaluator.invoke({"code": "total = 10 + 20\nprint(f'Sum: {total}')"})
    assert "Sum: 30" in res_stmt

    # Security boundary enforcement
    res_sec = code_sandbox_evaluator.invoke({"code": "import os; os.system('ls')"})
    assert "Security Restriction" in res_sec


def test_system_metrics_tool():
    metrics = system_metrics.invoke({})
    assert "OS Platform:" in metrics
    assert "CPU Cores:" in metrics
    assert "Python Engine:" in metrics


def test_agent_tool_loop_dispatch():
    mock_llm = MagicMock()
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{"name": "calculate", "args": {"expression": "50 + 50"}, "id": "call_abc"}],
    )
    final_msg = AIMessage(content="The calculation result is 100.")

    mock_bound = MagicMock()
    mock_bound.invoke.return_value = tool_call_msg
    mock_llm.bind_tools.return_value = mock_bound
    mock_llm.invoke.return_value = final_msg

    agent = ToolCallingAgent(llm=mock_llm)
    result = agent.run("Calculate 50 + 50")
    assert result == "The calculation result is 100."
    assert mock_bound.invoke.called
    assert mock_llm.invoke.called


def test_agent_tool_error_boundary():
    """Verify that when a tool raises an unhandled exception, the agent does NOT crash,
    but captures the error into a ToolMessage and allows the LLM to synthesize a response.
    """
    mock_llm = MagicMock()
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{"name": "failing_tool", "args": {"x": 1}, "id": "call_fail_1"}],
    )
    final_msg = AIMessage(content="I handled the failing tool gracefully.")

    mock_bound = MagicMock()
    mock_bound.invoke.return_value = tool_call_msg
    mock_llm.bind_tools.return_value = mock_bound
    mock_llm.invoke.return_value = final_msg

    # Create a mock tool that explicitly raises an unexpected exception
    failing_tool = MagicMock()
    failing_tool.name = "failing_tool"
    failing_tool.invoke.side_effect = RuntimeError("Simulated database connection failure")

    agent = ToolCallingAgent(llm=mock_llm, tools=[failing_tool])
    result = agent.run("Trigger failing tool")

    assert result == "I handled the failing tool gracefully."
    # Verify mock_llm.invoke received the ToolMessage with the error
    call_args = mock_llm.invoke.call_args[0][0]
    tool_msgs = [m for m in call_args if isinstance(m, ToolMessage)]
    assert len(tool_msgs) == 1
    assert "Simulated database connection failure" in tool_msgs[0].content
    assert tool_msgs[0].tool_call_id == "call_fail_1"


def test_tool_schema_generation():
    """Verify @tool correctly compiles type annotations and docstring into OpenAPI schema."""
    schema = calculate.args_schema.model_json_schema()
    assert "expression" in schema["properties"]
    assert schema["properties"]["expression"]["type"] == "string"
    assert "expression" in schema["required"]
