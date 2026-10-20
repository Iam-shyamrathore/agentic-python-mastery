"""Topic 08: Tool-Using Assistant (Complete Reference Solution).

Production-grade LangChain tool-calling agent with model binding,
multi-step tool execution, and fallback strategies.
"""

from __future__ import annotations

import argparse
import ast
import operator
import os
import platform
import sys
from typing import Any
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

load_dotenv()


# Safe math evaluator
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def safe_eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported operator: {op_type}")
    elif isinstance(node, ast.UnaryOp):
        operand = safe_eval(node.operand)
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type}")
    raise ValueError(f"Unsupported expression node: {type(node)}")


@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.
    
    Args:
        expression: A string expression like '24 * 7' or '100 / 4'
    """
    try:
        parsed = ast.parse(expression.strip(), mode="eval")
        result = safe_eval(parsed.body)
        return str(result)
    except Exception as exc:
        return f"Calculation error: {exc}"


@tool
def get_system_status() -> str:
    """Return the current operating status, OS, and Python version of the agent runtime."""
    return f"Status: Operational | OS: {platform.system()} {platform.release()} | Python: {platform.python_version()}"


def get_default_llm():
    """Detect available LLM provider and initialize ChatModel."""
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if groq_key:
        from langchain_groq import ChatGroq
        return ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_key, temperature=0.1)
    elif gemini_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_key, temperature=0.1)
    elif openai_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", api_key=openai_key, temperature=0.1)
    else:
        # Fallback to local Ollama
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(model="llama3.2:3b", temperature=0.1)


class ToolCallingAgent:
    """Agent that binds tools, analyzes user intent, and dispatches tool execution."""

    def __init__(self, llm=None) -> None:
        self.tools = [calculate, get_system_status]
        self.tools_by_name = {t.name: t for t in self.tools}
        self.base_llm = llm or get_default_llm()
        self.model_with_tools = self.base_llm.bind_tools(self.tools)

    def run(self, query: str) -> str:
        """Run the query through the tool loop and return the final answer."""
        messages: list[BaseMessage] = [
            SystemMessage(content="You are a helpful assistant equipped with tools. If a tool is relevant, use it."),
            HumanMessage(content=query),
        ]

        # Initial model call
        ai_msg = self.model_with_tools.invoke(messages)
        messages.append(ai_msg)

        # Check for requested tool calls
        if hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
            for tool_call in ai_msg.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                if tool_name in self.tools_by_name:
                    selected_tool = self.tools_by_name[tool_name]
                    tool_output = selected_tool.invoke(tool_args)
                else:
                    tool_output = f"Tool '{tool_name}' not recognized."

                messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_id))

            # Final synthesis step
            final_res = self.base_llm.invoke(messages)
            return final_res.content

        return ai_msg.content


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool-Calling AI Assistant")
    parser.add_argument("query", nargs="?", default="What is 144 divided by 12, and what OS is this machine running?")
    args = parser.parse_args()

    agent = ToolCallingAgent()
    print(f"Query: {args.query}\n")
    response = agent.run(args.query)
    print(f"🤖 Agent Response:\n{response}")


if __name__ == "__main__":
    main()
