"""Topic 08: Tool-Using Assistant (Starter Template).

Complete each TODO section alongside your AI Assistant.
This starter template introduces you to production-grade Tool Calling with LangChain:
1. How `@tool` parses Python type hints and docstrings into JSON Schemas.
2. Building multi-tool suites (math, system status, web search mock, code sandbox).
3. The Tool Calling Agent loop (Invoke -> Parse Tool Calls -> Execute -> Synthesize).
4. Tool Execution Error Boundaries (preventing crashes from bad arguments or runtime errors).
"""

from __future__ import annotations

import argparse
import ast
import io
import logging
import operator
import os
import platform
import sys
from typing import Any
from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool

# Set up educational logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("starter_tool_agent")

load_dotenv()


# ===========================================================================
# EDUCATIONAL GUIDE: How @tool Parses Python Signatures into JSON Schemas
# ===========================================================================
# When you write:
#     @tool
#     def calculate(expression: str) -> str:
#         """Evaluate a mathematical expression.
#         
#         Args:
#             expression: A string expression like '24 * 7'
#         """
#
# LangChain executes the following under the hood:
# 1. Type Introspection: It inspects Python type hints (`expression: str`).
#    Python types are mapped directly to JSON schema types:
#    - str -> "string"
#    - int -> "integer"
#    - float -> "number"
#    - bool -> "boolean"
#    - list[str] -> {"type": "array", "items": {"type": "string"}}
#    - Optional[T] -> marks the field as not required
# 2. Docstring Parsing: It parses Google or Sphinx-style docstrings to extract
#    the description of the tool and each parameter.
# 3. JSON Schema Assembly: It produces an OpenAPI-compatible function definition:
#    {
#      "type": "function",
#      "function": {
#        "name": "calculate",
#        "description": "Evaluate a mathematical expression.",
#        "parameters": {
#          "type": "object",
#          "properties": {
#            "expression": {"type": "string", "description": "A string expression like '24 * 7'"}
#          },
#          "required": ["expression"]
#        }
#      }
#    }
# 4. LLM Awareness: The LLM reads the description to decide *when* to invoke the tool,
#    and reads the parameters schema to produce valid JSON arguments.
# ===========================================================================


# ---------------------------------------------------------------------------
# Tool 1: Math Calculator
# ---------------------------------------------------------------------------
@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely.
    
    Args:
        expression: A string expression like '24 * 7', '100 / 4', or '2 ** 8'.
    """
    # TODO: Parse and evaluate mathematical expression safely using AST or basic arithmetic.
    # Hint: Avoid raw `eval()` in production! Use Python's `ast.parse(expression, mode='eval')`
    # and safely traverse supported operators (Add, Sub, Mult, Div, Pow).
    # Handle ZeroDivisionError and syntax errors gracefully.
    raise NotImplementedError("Implement calculate tool")


# ---------------------------------------------------------------------------
# Tool 2: System Status
# ---------------------------------------------------------------------------
@tool
def get_system_status() -> str:
    """Return the current operating status, OS, and Python version of the agent runtime."""
    # TODO: Return formatted status string:
    # "Status: Operational | OS: <OS> | Python: <version>"
    raise NotImplementedError("Implement get_system_status tool")


# ---------------------------------------------------------------------------
# Tool 3: Mock Web Search
# ---------------------------------------------------------------------------
@tool
def web_search_mock(query: str) -> str:
    """Simulate a web search engine query returning relevant external facts and URLs.
    
    Args:
        query: Search keywords or question to look up on the web.
    """
    # TODO: Look up query keywords in a mock dictionary or return a simulated
    # search result string with titles, URLs, and snippets.
    raise NotImplementedError("Implement web_search_mock tool")


# ---------------------------------------------------------------------------
# Tool 4: Safe Code Sandbox Evaluator
# ---------------------------------------------------------------------------
@tool
def code_sandbox_evaluator(code: str) -> str:
    """Safely evaluate isolated Python code or expressions and capture standard output.
    
    Args:
        code: Python code string to execute (e.g. '[x**2 for x in range(5)]').
    """
    # TODO: Check for forbidden tokens (e.g. "import os", "subprocess", "open(").
    # Execute safe code using restricted builtins and capture stdout with io.StringIO.
    raise NotImplementedError("Implement code_sandbox_evaluator tool")


# ---------------------------------------------------------------------------
# Tool 5: System Metrics
# ---------------------------------------------------------------------------
@tool
def system_metrics() -> str:
    """Retrieve detailed runtime host metrics including CPU architecture and memory availability."""
    # TODO: Collect CPU count, machine architecture, and platform string.
    raise NotImplementedError("Implement system_metrics tool")


# ---------------------------------------------------------------------------
# Tool-Calling Agent Loop
# ---------------------------------------------------------------------------
class ToolCallingAgent:
    """Agent that binds tools, analyzes user intent, and dispatches tool execution.
    
    EDUCATIONAL GUIDE: Tool Execution Error Boundaries
    ---------------------------------------------------
    Why do we need an error boundary around tool execution?
    In autonomous agents, if a tool throws an unhandled exception (e.g. timeout,
    type error, network disconnect), the entire agent process crashes.
    
    Production Pattern:
    1. Wrap `selected_tool.invoke(tool_args)` in a `try...except Exception as exc:` block.
    2. Instead of crashing, format the exception as:
       `ToolMessage(content=f"Tool error: {exc}", tool_call_id=tool_id)`
    3. Return this ToolMessage to the LLM.
    4. The LLM sees the error message, understands what went wrong, and can retry
       with corrected arguments or gracefully inform the user!
    """

    def __init__(self, llm=None, tools: list | None = None) -> None:
        """Initialize the agent with tools and bound LLM.
        
        TODO:
        1. Store `self.tools` (defaulting to the 5 tools above).
        2. Create lookup dict `self.tools_by_name = {t.name: t for t in self.tools}`.
        3. Store `self.base_llm` (either passed in or initialized via default ChatModel).
        4. Bind tools: `self.model_with_tools = self.base_llm.bind_tools(self.tools)`.
        """
        raise NotImplementedError("Implement __init__ tool binding")

    def run(self, query: str) -> str:
        """Run the query through the tool loop with resilient error boundaries.
        
        TODO:
        1. Build message history: `[SystemMessage(...), HumanMessage(content=query)]`.
        2. Invoke model: `ai_msg = self.model_with_tools.invoke(messages)`.
        3. Append `ai_msg` to `messages`.
        4. If `ai_msg` has `tool_calls`:
           For each `call` in `ai_msg.tool_calls`:
             a. Extract `tool_name = call['name']`, `tool_args = call['args']`, `tool_id = call['id']`.
             b. Execute tool within a `try...except` error boundary:
                `tool_output = self.tools_by_name[tool_name].invoke(tool_args)`
             c. Append `ToolMessage(content=str(tool_output), tool_call_id=tool_id)`.
           Synthesize final answer:
             `final_msg = self.base_llm.invoke(messages)`
             return final_msg.content
        5. If no tool calls, return `ai_msg.content`.
        """
        raise NotImplementedError("Implement run tool loop")


def main() -> None:
    print("Welcome to Tool-Using Assistant! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
