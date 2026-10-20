"""Topic 08: Tool-Using Assistant (Complete Reference Solution).

Production-grade LangChain tool-calling agent featuring:
1. Multi-tool suite: calculate, get_system_status, web_search_mock,
   code_sandbox_evaluator, and system_metrics.
2. Tool execution error boundaries: Catches exceptions in tool execution
   and returns structured ToolMessage errors to the LLM to prevent agent crashes.
3. In-depth architectural docstrings explaining JSON schema generation from
   type annotations, function call parsing, and tool execution loops.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
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

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tool_agent")

load_dotenv()


# ---------------------------------------------------------------------------
# Tool 1: Safe Mathematical Evaluator
# ---------------------------------------------------------------------------
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}


def safe_eval(node: ast.AST) -> float | int:
    """Recursively evaluate an AST expression using only whitelisted operators."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Division by zero in mathematical expression.")
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
    elif isinstance(node, ast.UnaryOp):
        operand = safe_eval(node.operand)
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely using an AST-based parser.
    
    Args:
        expression: A string expression such as '24 * 7', '100 / 4', or '2 ** 8'.
        
    Returns:
        The string representation of the computed numerical result or error message.
    """
    try:
        parsed = ast.parse(expression.strip(), mode="eval")
        result = safe_eval(parsed.body)
        return str(result)
    except Exception as exc:
        return f"Calculation error: {exc}"


# ---------------------------------------------------------------------------
# Tool 2: System Status
# ---------------------------------------------------------------------------
@tool
def get_system_status() -> str:
    """Return the current operating status, OS, and Python version of the agent runtime."""
    return (
        f"Status: Operational | OS: {platform.system()} {platform.release()} "
        f"({platform.machine()}) | Python: {platform.python_version()}"
    )


# ---------------------------------------------------------------------------
# Tool 3: Mock Web Search
# ---------------------------------------------------------------------------
MOCK_SEARCH_DATABASE = {
    "python": [
        {"title": "Python 3.12 Release Highlights", "url": "https://python.org/news/3.12", "snippet": "Python 3.12 introduces isolated subinterpreters, improved error messages, and Linux perf profiler support."},
        {"title": "Real Python Tutorials", "url": "https://realpython.com", "snippet": "Production Python guidelines covering async programming, type annotations, and modern packaging with uv."},
    ],
    "langchain": [
        {"title": "LangChain Documentation", "url": "https://python.langchain.com", "snippet": "LangChain simplifies building LLM applications via standard components for tool calling, memory, and chains."},
        {"title": "LangChain Tool Calling Guide", "url": "https://python.langchain.com/docs/how_to/tool_calling", "snippet": "Bind tools to ChatModels and process tool calls reliably using ToolMessage."},
    ],
    "fastapi": [
        {"title": "FastAPI Web Framework", "url": "https://fastapi.tiangolo.com", "snippet": "High-performance API framework built on Starlette and Pydantic with automated OpenAPI docs."},
    ],
    "rag": [
        {"title": "Retrieval-Augmented Generation Architecture", "url": "https://arxiv.org/abs/2005.11401", "snippet": "RAG combines parametric memory (LLM weights) with non-parametric memory (vector database retrieval)."},
    ],
}


@tool
def web_search_mock(query: str) -> str:
    """Simulate a web search engine query returning relevant external facts and URLs.
    
    Args:
        query: Search keywords or question to look up on the web.
        
    Returns:
        Formatted search snippet string with titles and source URLs.
    """
    query_lower = query.lower()
    matches = []

    for keyword, entries in MOCK_SEARCH_DATABASE.items():
        if keyword in query_lower:
            matches.extend(entries)

    if not matches:
        return (
            f"Search results for '{query}':\n"
            f"- Title: General Reference on '{query}'\n"
            f"  URL: https://en.wikipedia.org/wiki/{query.replace(' ', '_')}\n"
            f"  Snippet: Verified technical reference information related to {query}."
        )

    formatted = [f"Search results for '{query}':"]
    for i, m in enumerate(matches[:3], 1):
        formatted.append(f"{i}. [{m['title']}]({m['url']})\n   {m['snippet']}")

    return "\n".join(formatted)


# ---------------------------------------------------------------------------
# Tool 4: Safe Code Sandbox Evaluator
# ---------------------------------------------------------------------------
DISALLOWED_CODE_TOKENS = {
    "import os",
    "import sys",
    "import subprocess",
    "import shutil",
    "__import__",
    "open(",
    "eval(",
    "exec(",
    "breakpoint(",
}


@tool
def code_sandbox_evaluator(code: str) -> str:
    """Safely evaluate isolated Python code or expressions and capture standard output.
    
    Args:
        code: Python code string to execute (e.g. '[x**2 for x in range(5)]').
        
    Returns:
        Captured stdout or evaluated return value, or a security/syntax error message.
    """
    code_clean = code.strip()

    # Security boundary: Block destructive system/file primitives
    for token in DISALLOWED_CODE_TOKENS:
        if token in code_clean:
            return f"Security Restriction: Use of '{token}' is prohibited in the code sandbox."

    # Sandbox environment with limited safe builtins
    safe_builtins = {
        "abs": abs,
        "all": all,
        "any": any,
        "bin": bin,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "print": print,
        "range": range,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
    }
    sandbox_globals = {"__builtins__": safe_builtins}
    sandbox_locals: dict[str, Any] = {}

    stdout_buffer = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout_buffer):
            # Attempt to evaluate as expression first
            try:
                compiled_expr = compile(code_clean, "<sandbox>", "eval")
                result = eval(compiled_expr, sandbox_globals, sandbox_locals)
                captured_out = stdout_buffer.getvalue().strip()
                if captured_out:
                    return f"{captured_out}\nResult: {result}"
                return f"Result: {result}"
            except SyntaxError:
                # Fall back to multi-statement execution
                compiled_exec = compile(code_clean, "<sandbox>", "exec")
                exec(compiled_exec, sandbox_globals, sandbox_locals)
                captured_out = stdout_buffer.getvalue().strip()
                if captured_out:
                    return f"Output:\n{captured_out}"
                return "Code executed successfully (no output)."
    except Exception as exc:
        return f"Execution Error ({type(exc).__name__}): {exc}"


# ---------------------------------------------------------------------------
# Tool 5: Detailed System Metrics
# ---------------------------------------------------------------------------
@tool
def system_metrics() -> str:
    """Retrieve detailed runtime host metrics including CPU architecture and memory availability.
    
    Returns:
        Structured system health and host hardware summary.
    """
    cpu_count = os.cpu_count() or 1
    sys_platform = platform.platform()
    machine = platform.machine()
    python_impl = platform.python_implementation()

    metrics = [
        f"OS Platform: {sys_platform}",
        f"Architecture: {machine}",
        f"CPU Cores: {cpu_count}",
        f"Python Engine: {python_impl} {platform.python_version()}",
    ]

    try:
        import psutil
        vm = psutil.virtual_memory()
        metrics.append(f"RAM Total: {vm.total / (1024**3):.1f} GB")
        metrics.append(f"RAM Used: {vm.percent}%")
    except ImportError:
        metrics.append("RAM Metrics: psutil not installed (OS fallback active)")

    return " | ".join(metrics)


# ---------------------------------------------------------------------------
# LLM Provider Initialization
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Tool Calling Agent with Error Boundaries
# ---------------------------------------------------------------------------
class ToolCallingAgent:
    """Production-grade agent that binds tools, dispatches executions,
    and isolates errors using structured ToolMessage boundaries.
    
    Educational Architecture Note:
    -------------------------------
    1. Tool Schema Generation:
       When `@tool` decorates a function, LangChain inspects:
       - Function name (`func.__name__`)
       - Docstring description (`func.__doc__`)
       - Argument type annotations (`func.__annotations__`)
       This compiles into a standardized OpenAPI Function Schema:
       ```json
       {
         "type": "function",
         "function": {
           "name": "calculate",
           "description": "Evaluate a mathematical expression...",
           "parameters": {
             "type": "object",
             "properties": {"expression": {"type": "string"}},
             "required": ["expression"]
           }
         }
       }
       ```
    2. Model Binding:
       `self.base_llm.bind_tools(self.tools)` sends these JSON schemas to the provider.
       The model decides whether to respond with conversational text OR emit a structured
       tool call (`AIMessage.tool_calls = [{'name': '...', 'args': {...}, 'id': '...'}]`).
       
    3. Tool Execution Error Boundary:
       In production, external tools will fail (e.g. database disconnect, API timeout,
       bad LLM parameters, division by zero).
       IF AN AGENT CRASHES ON A TOOL EXCEPTION, the entire workflow fails.
       INSTEAD, we catch exceptions at the tool boundary, package the error into a
       `ToolMessage(content="Error: ...", tool_call_id=id)`, and pass it back to the LLM.
       The model can then inspect the error, self-correct, and try a different tool or notify the user!
    """

    def __init__(self, llm=None, tools: list | None = None) -> None:
        self.tools = tools or [
            calculate,
            get_system_status,
            web_search_mock,
            code_sandbox_evaluator,
            system_metrics,
        ]
        self.tools_by_name = {t.name: t for t in self.tools}
        self.base_llm = llm or get_default_llm()
        self.model_with_tools = self.base_llm.bind_tools(self.tools)
        logger.info(
            "Initialized ToolCallingAgent with %d tools: %s",
            len(self.tools),
            list(self.tools_by_name.keys()),
        )

    def run(self, query: str) -> str:
        """Run the query through the tool loop with resilient error boundaries."""
        messages: list[BaseMessage] = [
            SystemMessage(
                content=(
                    "You are an expert AI assistant equipped with specialized tools. "
                    "When a user query requires facts, calculations, code execution, or system metrics, "
                    "call the relevant tool. If a tool reports an error, explain the issue clearly."
                )
            ),
            HumanMessage(content=query),
        ]

        logger.info("Agent invoked with query: '%s'", query)

        # Step 1: Initial LLM invocation with tool schemas bound
        try:
            ai_msg = self.model_with_tools.invoke(messages)
        except Exception as exc:
            logger.error("Initial LLM invocation failed: %s", exc)
            return f"Agent invocation error: {exc}"

        messages.append(ai_msg)

        # Step 2: Check for tool calls in LLM output
        if hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
            logger.info("LLM requested %d tool calls", len(ai_msg.tool_calls))

            for tool_call in ai_msg.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "call_unknown")

                logger.info("Executing tool: '%s' with args: %s", tool_name, tool_args)

                # Tool Execution Error Boundary
                if tool_name in self.tools_by_name:
                    selected_tool = self.tools_by_name[tool_name]
                    try:
                        tool_output = selected_tool.invoke(tool_args)
                    except Exception as tool_exc:
                        logger.warning(
                            "Tool '%s' encountered an exception (%s). Capturing in error boundary.",
                            tool_name,
                            tool_exc,
                        )
                        tool_output = (
                            f"ToolExecutionError in '{tool_name}': {type(tool_exc).__name__}: {tool_exc}. "
                            "Please review your arguments and try again."
                        )
                else:
                    logger.warning("Requested tool '%s' not registered in agent toolset", tool_name)
                    tool_output = (
                        f"Error: Tool '{tool_name}' is not recognized. "
                        f"Available tools: {list(self.tools_by_name.keys())}"
                    )

                messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_id))

            # Step 3: Synthesis step - LLM interprets tool outputs
            try:
                final_res = self.base_llm.invoke(messages)
                return getattr(final_res, "content", str(final_res))
            except Exception as synth_exc:
                logger.error("Synthesis LLM invocation failed: %s", synth_exc)
                return f"Synthesis error: {synth_exc}"

        return getattr(ai_msg, "content", str(ai_msg))


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Tool-Calling AI Assistant")
    parser.add_argument(
        "query",
        nargs="?",
        default="Calculate 25 * 14, check system metrics, and tell me about Python 3.12 features.",
    )
    args = parser.parse_args()

    agent = ToolCallingAgent()
    print(f"Query: {args.query}\n")
    response = agent.run(args.query)
    print(f"🤖 Agent Response:\n{response}")


if __name__ == "__main__":
    main()
