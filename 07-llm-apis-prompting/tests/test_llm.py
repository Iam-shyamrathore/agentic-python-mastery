"""Tests for Topic 07: LLM APIs & Prompting."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from openai import RateLimitError

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from ai_assistant import (
    TaskBreakdown,
    TaskStep,
    TokenUsage,
    UnifiedLLMClient,
    estimate_tokens,
)


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
    mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    client.client.chat.completions.create = MagicMock(return_value=mock_resp)

    reply = client.chat("Hi")
    assert reply == "Hello AI Engineer!"
    assert client.client.chat.completions.create.called
    assert client.last_usage is not None
    assert client.last_usage.prompt_tokens == 10
    assert client.last_usage.completion_tokens == 5
    assert client.last_usage.total_tokens == 15
    assert not client.last_usage.estimated


def test_token_estimation_fallback():
    # Empty string
    assert estimate_tokens("") == 0

    # Non-empty text
    text = "Building autonomous agents with LangGraph and FastAPI is powerful."
    count = estimate_tokens(text)
    assert count > 5


def test_generate_plan_mocked():
    client = UnifiedLLMClient(provider="ollama")
    plan_dict = {
        "task_goal": "Deploy Docker Microservice",
        "difficulty": "Easy",
        "steps": [
            {"step_num": 1, "title": "Dockerfile", "description": "Write multi-stage Dockerfile"},
            {"step_num": 2, "title": "Build", "description": "Run docker build -t app:latest ."},
        ],
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(plan_dict)))]
    mock_resp.usage = MagicMock(prompt_tokens=80, completion_tokens=40, total_tokens=120)
    client.client.chat.completions.create = MagicMock(return_value=mock_resp)

    plan = client.generate_plan("Deploy Docker Microservice")
    assert isinstance(plan, TaskBreakdown)
    assert plan.task_goal == "Deploy Docker Microservice"
    assert len(plan.steps) == 2
    assert client.last_usage.total_tokens == 120


def test_retry_on_transient_error():
    client = UnifiedLLMClient(provider="ollama")
    success_resp = MagicMock()
    success_resp.choices = [MagicMock(message=MagicMock(content="Recovered after rate limit!"))]
    success_resp.usage = MagicMock(prompt_tokens=5, completion_tokens=5, total_tokens=10)

    # Mock response to raise RateLimitError on first call, succeed on second
    error_response = MagicMock(status_code=429, headers={})
    rate_limit_err = RateLimitError(
        message="Rate limit reached",
        response=error_response,
        body={"error": {"message": "Rate limit reached"}},
    )

    client.client.chat.completions.create = MagicMock(
        side_effect=[rate_limit_err, success_resp]
    )

    reply = client.chat("Try request")
    assert reply == "Recovered after rate limit!"
    assert client.client.chat.completions.create.call_count == 2
