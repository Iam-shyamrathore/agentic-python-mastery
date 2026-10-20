"""Tests for Topic 08: LangChain & Tool Calling."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from langchain_core.messages import AIMessage

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from tool_agent import ToolCallingAgent, calculate, get_system_status


def test_calculate_tool():
    res1 = calculate.invoke({"expression": "12 * 12"})
    assert res1 == "144"

    res2 = calculate.invoke({"expression": "100 / 4"})
    assert res2 == "25.0"


def test_system_status_tool():
    status = get_system_status.invoke({})
    assert "Status: Operational" in status
    assert "Python:" in status


def test_agent_tool_loop_dispatch():
    # Mock LLM that returns a tool call on first invocation and final text on second
    mock_llm = MagicMock()
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{"name": "calculate", "args": {"expression": "50 + 50"}, "id": "call_abc"}],
    )
    final_msg = AIMessage(content="The calculation result is 100.")

    # Model with tools returns tool_call_msg
    mock_bound = MagicMock()
    mock_bound.invoke.return_value = tool_call_msg
    mock_llm.bind_tools.return_value = mock_bound
    mock_llm.invoke.return_value = final_msg

    agent = ToolCallingAgent(llm=mock_llm)
    result = agent.run("Calculate 50 + 50")
    assert result == "The calculation result is 100."
    assert mock_bound.invoke.called
    assert mock_llm.invoke.called
