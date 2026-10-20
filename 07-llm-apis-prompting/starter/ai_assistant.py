"""Topic 07: AI Text Assistant (Starter Template).

Complete each TODO section alongside your AI Assistant.
"""

from __future__ import annotations

import os
from typing import Any, Iterator
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()


class TaskStep(BaseModel):
    step_num: int
    title: str
    description: str


class TaskBreakdown(BaseModel):
    task_goal: str
    difficulty: str = Field(description="Easy, Medium, or Hard")
    steps: list[TaskStep]


class UnifiedLLMClient:
    """Multi-provider client supporting Groq, OpenRouter, Ollama, and OpenAI."""

    def __init__(self) -> None:
        # TODO: Detect which provider key is available in environment
        # Priority: GROQ_API_KEY -> OPENROUTER_API_KEY -> OPENAI_API_KEY -> Local Ollama
        raise NotImplementedError("Implement __init__ provider detection")

    def chat(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> str:
        """Send chat completion and return response string."""
        # TODO: Send messages to LLM and return content string
        raise NotImplementedError("Implement chat")

    def chat_stream(self, prompt: str, system_prompt: str = "") -> Iterator[str]:
        """Stream chunks from LLM completion."""
        # TODO: Stream delta tokens
        raise NotImplementedError("Implement chat_stream")

    def generate_plan(self, goal: str) -> TaskBreakdown:
        """Generate structured breakdown using TaskBreakdown schema."""
        # TODO: Prompt LLM for JSON matching TaskBreakdown and validate
        raise NotImplementedError("Implement generate_plan")


def main() -> None:
    print("Welcome to AI Text Assistant! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
