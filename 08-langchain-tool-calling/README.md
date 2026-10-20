# 🛠️ Topic 08: LangChain & Tool Calling for AI Engineers

> **Master LangChain Expression Language (LCEL), the `@tool` decorator, native function calling bindings, and agent execution loops.**

---

## 🎯 Why Tool Calling is the Bridge to Autonomous Agents

Standard LLMs are locked in an isolated box—they have knowledge cutoff dates and cannot interact with the real world.
**Tool Calling** gives models hands and eyes:
- Calculating complex math deterministically
- Querying a live database
- Searching the live web
- Sending emails or executing bash scripts

In this module, you will understand how modern tool calling works under the hood without relying on black-box abstractions.

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. Defining Tools with `@tool`

```python
from langchain_core.tools import tool

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.
    
    Args:
        expression: A math string like '45 * 12' or '100 / 4'
    """
    try:
        # Safe math evaluation using limited builtins
        allowed = {"__builtins__": None}
        result = eval(expression, allowed, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"
```

---

### 2. Binding Tools to Models

Modern ChatModels accept tools via `.bind_tools()`:

```python
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# Initialize model
llm = ChatGroq(model="llama-3.3-70b-versatile")

# Bind tools
model_with_tools = llm.bind_tools([calculate])

# Invocation
response = model_with_tools.invoke([HumanMessage(content="What is 452 multiplied by 18?")])
print(response.tool_calls)
# Output: [{'name': 'calculate', 'args': {'expression': '452 * 18'}, 'id': 'call_123'}]
```

---

### 3. The Tool Loop Mechanics

```
User Prompt
    │
    ▼
[ChatModel + Tools] ──► Does model request a tool?
    │                           │
    ├───────── NO ──────────────┤
    │                           ▼ YES
    │                    [Execute Tool in Python]
    │                           │
    │                    [Return ToolMessage]
    ▼                           │
[Final Answer] ◄────────────────┘
```

---

## 🛠️ The Hands-on Project: Tool-Using Assistant

In this module, you will build `starter/tool_agent.py`:
- Custom Python tools for math and system inspection
- Model binding with free-tier Groq / Gemini / Ollama
- Full dispatch loop executing tool calls and feeding responses back to the LLM
- Automated test coverage

### Running the Tests
```bash
pytest 08-langchain-tool-calling/tests/test_tool_agent.py -v
```
