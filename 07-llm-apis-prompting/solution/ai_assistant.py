"""Topic 07: AI Text Assistant (Complete Reference Solution).

Production-grade multi-provider LLM interface supporting free Groq, OpenRouter,
Ollama, and OpenAI with streaming and Pydantic structured output parsing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
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

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        groq_key = os.getenv("GROQ_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if provider == "groq" or (provider is None and groq_key):
            self.provider = "groq"
            self.model = model or "llama-3.3-70b-versatile"
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key or "dummy_key",
            )
        elif provider == "openrouter" or (provider is None and openrouter_key):
            self.provider = "openrouter"
            self.model = model or "meta-llama/llama-3.2-3b-instruct:free"
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key or "dummy_key",
            )
        elif provider == "openai" or (provider is None and openai_key):
            self.provider = "openai"
            self.model = model or "gpt-4o-mini"
            self.client = OpenAI(api_key=openai_key or "dummy_key")
        else:
            # Fallback to local Ollama
            self.provider = "ollama"
            self.model = model or "llama3.2:3b"
            self.client = OpenAI(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                api_key="ollama",
            )

    def chat(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> str:
        """Send chat completion and return response string."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content or ""

    def chat_stream(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> Iterator[str]:
        """Stream chunks from LLM completion."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def generate_plan(self, goal: str) -> TaskBreakdown:
        """Generate structured breakdown using TaskBreakdown schema."""
        prompt = (
            f"Break down the following goal into a structured plan: '{goal}'.\n"
            f"You MUST return valid JSON adhering strictly to this schema:\n"
            f"{json.dumps(TaskBreakdown.model_json_schema())}"
        )
        messages = [
            {"role": "system", "content": "You are a technical planner. You only speak valid JSON."},
            {"role": "user", "content": prompt},
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_json = response.choices[0].message.content or "{}"
        return TaskBreakdown.model_validate_json(raw_json)


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-Provider AI Text Assistant")
    parser.add_argument("prompt", nargs="?", default="Explain RAG in one short paragraph.")
    parser.add_argument("--stream", action="store_true", help="Stream response")
    parser.add_argument("--plan", action="store_true", help="Generate structured task plan")
    args = parser.parse_args()

    assistant = UnifiedLLMClient()
    print(f"🧠 Using Provider: [{assistant.provider}] with Model: [{assistant.model}]\n")

    if args.plan:
        print(f"📋 Generating structured plan for: '{args.prompt}'...")
        plan = assistant.generate_plan(args.prompt)
        print(f"\nGoal: {plan.task_goal} (Difficulty: {plan.difficulty})")
        for s in plan.steps:
            print(f"  Step {s.step_num}: {s.title} - {s.description}")
    elif args.stream:
        print("💬 Streaming response:")
        for token in assistant.chat_stream(args.prompt):
            print(token, end="", flush=True)
        print()
    else:
        result = assistant.chat(args.prompt)
        print(f"💬 Response:\n{result}")


if __name__ == "__main__":
    main()
