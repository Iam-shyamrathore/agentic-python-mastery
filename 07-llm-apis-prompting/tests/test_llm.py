"""Tests for Topic 07: LLM APIs & Prompting."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from ai_assistant import TaskBreakdown, TaskStep, UnifiedLLMClient


def test_task_breakdown_schema_validation():
    valid_payload = {
        "task_goal": "Build Agent",
        "difficulty": "Medium",
        "steps": [
            {"step_num": 1, "title": "Setup", "description": "Initialize repo"},
            {"step_num": 2, "title": "Tools", "description": "Add web search"},
        ],
    }
    model = TaskBreakdown.model_validate(valid_payload)
    assert model.task_goal == "Build Agent"
    assert len(model.steps) == 2
    assert model.steps[0].step_num == 1


def test_unified_client_with_mock():
    client = UnifiedLLMClient(provider="ollama")
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Hello AI Engineer!"))]
    client.client.chat.completions.create = MagicMock(return_value=mock_resp)

    reply = client.chat("Hi")
    assert reply == "Hello AI Engineer!"
    assert client.client.chat.completions.create.called
