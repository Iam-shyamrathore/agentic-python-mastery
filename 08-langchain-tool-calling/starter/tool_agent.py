"""Topic 08: Tool-Using Assistant (Starter Template).

Complete each TODO section alongside your AI Assistant.
"""

from __future__ import annotations

import os
from typing import Any
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

load_dotenv()


@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.
    
    Args:
        expression: A string expression like '24 * 7' or '100 / 4'
    """
    # TODO: Safely evaluate math expression and return string result
    raise NotImplementedError("Implement calculate tool")


@tool
def get_system_status() -> str:
    """Return the current operating status of the AI agent runtime."""
    # TODO: Return health status string
    raise NotImplementedError("Implement get_system_status tool")


class ToolCallingAgent:
    """Agent that binds tools, analyzes user intent, and dispatches tool execution."""

    def __init__(self) -> None:
        self.tools = [calculate, get_system_status]
        self.tools_by_name = {t.name: t for t in self.tools}
        # TODO: Initialize ChatModel and bind self.tools

    def run(self, query: str) -> str:
        """Run the query through the tool loop and return the final answer."""
        # TODO: Implement tool call check -> execute tool -> synthesize final response
        raise NotImplementedError("Implement run tool loop")


def main() -> None:
    print("Welcome to Tool-Using Assistant! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
