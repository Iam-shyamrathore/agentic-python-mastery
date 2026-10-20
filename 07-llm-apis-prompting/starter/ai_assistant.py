"""Topic 07: AI Text Assistant (Starter Template).

Complete each TODO section alongside your AI Assistant.
This starter template introduces you to production-grade LLM engineering patterns:
1. Multi-provider switching (Groq, OpenRouter, OpenAI, Ollama).
2. Streaming token generation for low Time-to-First-Token (TTFT).
3. Structured output generation with Pydantic JSON schema constraints.
4. Token estimation and usage tracking.
5. Few-shot prompt engineering and system message guardrails.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Iterator
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# Set up educational logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("starter_assistant")

load_dotenv()


# ---------------------------------------------------------------------------
# Token Usage Model & Estimation
# ---------------------------------------------------------------------------
class TokenUsage(BaseModel):
    """Tracks token consumption metrics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated: bool = False


def estimate_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Estimate token count using tiktoken if installed, or character heuristic (~4 chars/token).
    
    Why this matters in production:
    LLMs have hard context limits. Sending a prompt that exceeds the window triggers
    immediate HTTP 400 errors. Estimating tokens client-side lets you truncate history
    or switch to larger-context models before making expensive network calls.
    """
    if not text:
        return 0
    try:
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Rule of thumb: English text averages ~4 characters per token
        return max(1, (len(text) + 3) // 4)


# ---------------------------------------------------------------------------
# Pydantic Schemas for Structured Output
# ---------------------------------------------------------------------------
class TaskStep(BaseModel):
    """Single discrete step in an execution plan."""

    step_num: int = Field(..., description="Step sequence number (1-indexed)")
    title: str = Field(..., description="Short descriptive title of the action")
    description: str = Field(..., description="Execution details and verification criteria")


class TaskBreakdown(BaseModel):
    """Structured plan output contract.
    
    EDUCATIONAL NOTE: Pydantic Schema Serialization for LLMs
    ---------------------------------------------------------
    How do we reliably transmit data models to an LLM?
    Calling `TaskBreakdown.model_json_schema()` produces a standard JSON Schema
    specification (including property names, types, descriptions, and required fields).
    
    When passed into an LLM system prompt or `response_format`, modern inference
    engines use Constrained Decoding (Grammar-based sampling) to mask invalid tokens
    at every generation step. This completely eliminates missing keys and hallucinated
    field names.
    """

    task_goal: str = Field(..., description="High-level goal being decomposed")
    difficulty: str = Field(..., description="'Easy', 'Medium', or 'Hard'")
    steps: list[TaskStep] = Field(..., description="Ordered list of steps to accomplish the goal")


# ---------------------------------------------------------------------------
# Multi-Provider Client
# ---------------------------------------------------------------------------
class UnifiedLLMClient:
    """Multi-provider client supporting Groq, OpenRouter, Ollama, and OpenAI."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize LLM client with provider auto-detection.
        
        TODO: Inspect environment variables and configure self.client:
        - Priority:
            1. If provider=="groq" or GROQ_API_KEY is set:
               base_url="https://api.groq.com/openai/v1", default model="llama-3.3-70b-versatile"
            2. If provider=="openrouter" or OPENROUTER_API_KEY is set:
               base_url="https://openrouter.ai/api/v1", default model="meta-llama/llama-3.2-3b-instruct:free"
            3. If provider=="openai" or OPENAI_API_KEY is set:
               default model="gpt-4o-mini"
            4. Otherwise fallback to Ollama:
               base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"), model="llama3.2:3b"
               
        Hint: Initialize self.client as `OpenAI(base_url=..., api_key=...)`.
        Also initialize `self.last_usage: TokenUsage | None = None`.
        """
        raise NotImplementedError("Implement __init__ provider detection")

    def chat(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> str:
        """Send chat completion and return response string.
        
        TODO:
        1. Construct message list with system prompt and user prompt:
           `[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]`
        2. Call `self.client.chat.completions.create(model=self.model, messages=messages, temperature=0.7)`
        3. Extract `response.choices[0].message.content or ""`
        4. Track token usage from `response.usage` or via `estimate_tokens`
        5. Return the response string
        
        Production Considerations:
        - Transient Errors: Model providers occasionally return 429 (Rate Limit) or 503 (Overloaded).
          In production, wrap this call with a retry decorator (e.g. `tenacity.retry`) with exponential backoff.
        """
        raise NotImplementedError("Implement chat")

    def chat_stream(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> Iterator[str]:
        """Stream chunks from LLM completion.
        
        TODO:
        1. Call `self.client.chat.completions.create(..., stream=True)`
        2. Iterate over the stream chunks:
           for chunk in stream:
               delta = chunk.choices[0].delta.content
               if delta:
                   yield delta
        """
        raise NotImplementedError("Implement chat_stream")

    def generate_plan(self, goal: str) -> TaskBreakdown:
        """Generate structured breakdown using TaskBreakdown schema.
        
        EDUCATIONAL GUIDE: Few-Shot Prompting & System Message Constraints
        -------------------------------------------------------------------
        1. System Message Constraints:
           Always anchor the agent's behavior firmly:
           "You are a technical planner. You speak ONLY in valid JSON matching the exact schema."
           Instructing the model to omit conversational chit-chat ('Sure! Here is your plan...')
           prevents JSON parse errors.
           
        2. Embedding the Schema:
           Serialize the schema: `json_schema = json.dumps(TaskBreakdown.model_json_schema())`
           Include it in the system prompt so the LLM understands expected field names and data types.
           
        3. Few-Shot Demonstration:
           LLMs learn exceptionally well by example. Including one minimal valid JSON example
           in the system prompt dramatically reduces syntax errors on smaller open-weight models.
           
        4. Constrained Decoding:
           Pass `response_format={"type": "json_object"}` in `chat.completions.create(...)`.
           
        5. Validation:
           Parse and validate raw string with `TaskBreakdown.model_validate_json(raw_json)`.
        """
        raise NotImplementedError("Implement generate_plan")


def main() -> None:
    print("Welcome to AI Text Assistant! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
