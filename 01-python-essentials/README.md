# 🐍 Topic 01: Python Essentials for AI Engineers

> **Master the fundamental Python idioms, data structures, type hints, dataclasses, and error handling patterns essential for AI systems.**

---

## 🎯 Why This Topic Matters in AI Engineering

AI Engineering is NOT just calling `model.generate()`. Real-world AI applications require:
- Parsing messy JSON responses from LLMs
- Strict data contracts using Type Hints and Dataclasses
- Defensive exception handling when external model APIs fail or return malformed outputs
- Efficient manipulation of token sequences, embedding matrices, and state dictionaries
- Clean CLI tooling for benchmarking, agent orchestration, and evaluation pipelines

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. Modern Type Hinting (`typing`)

Python is dynamically typed, but modern AI engineering codebases (LangChain, LlamaIndex, FastAPI, Pydantic) are 100% strictly typed.

```python
from typing import Optional, Union, Literal, Any, Callable
from datetime import datetime

# Primitive types
user_id: str = "usr_123"
token_count: int = 1540
temperature: float = 0.7
is_stream: bool = True

# Complex collections (Python 3.9+ native syntax)
tags: list[str] = ["ai", "python", "rag"]
metadata: dict[str, Any] = {"model": "llama-3.3", "latency_ms": 230}
coordinates: tuple[float, float] = (37.7749, -122.4194)
unique_ids: set[str] = {"doc_1", "doc_2"}

# Modern Union and Optional
response_text: str | None = None          # Preferred Python 3.10+ syntax
fallback_val: Union[int, float] = 3.14

# Literals for restricted choices
RoleType = Literal["system", "user", "assistant", "tool"]
current_role: RoleType = "system"  # Type checker flags any other string!
```

---

### 2. Modern Dataclasses & Data Modeling

Dataclasses eliminate boilerplate `__init__`, `__repr__`, and `__eq__` methods. They are the ideal way to represent LLM messages, memory logs, and agent state objects.

```python
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import uuid

@dataclass
class ChatMessage:
    role: str
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert dataclass instance to a clean JSON-serializable dict."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatMessage":
        """Instantiate directly from a serialized dictionary."""
        data_copy = data.copy()
        if "created_at" in data_copy and isinstance(data_copy["created_at"], str):
            data_copy["created_at"] = datetime.fromisoformat(data_copy["created_at"])
        return cls(**data_copy)
```

---

### 3. Defensive Error Handling & Custom Exceptions

LLM calls, token parsing, and network responses fail frequently. Never catch generic `Exception` blindly. Always create domain-specific exceptions.

```python
class AgenticBaseError(Exception):
    """Base exception for all domain errors."""
    pass

class TaskNotFoundError(AgenticBaseError):
    def __init__(self, task_id: str):
        super().__init__(f"Task with ID '{task_id}' was not found in storage.")
        self.task_id = task_id

class InvalidStateTransitionError(AgenticBaseError):
    pass

# Safe execution pattern
try:
    # Attempt operation
    raise TaskNotFoundError("task_999")
except TaskNotFoundError as exc:
    print(f"Handled error: {exc}")
except AgenticBaseError as exc:
    print(f"Domain error occurred: {exc}")
except Exception as exc:
    print(f"Unexpected system error: {exc}")
finally:
    print("Cleanup actions (close connections, flush logs)...")
```

---

## 🛠️ The Hands-on Project: CLI Task Manager

In this module, you will build a robust, modular Command Line Interface (CLI) Task Manager featuring:
- Typed data models (`Task`, `TaskStatus`, `TaskPriority`)
- Full CRUD operations (Create, Read, Update, Delete)
- Persistent JSON file storage with atomic writes
- Filtering by status, priority, and search terms
- Rich terminal formatting with error resilience

### Directory Layout
- `starter/task_manager.py` — Your workspace. Follow the `TODO` blocks!
- `solution/task_manager.py` — Complete, reference implementation.
- `tests/test_task_manager.py` — Automated verification tests.

### Running the Tests
```bash
pytest 01-python-essentials/tests/test_task_manager.py -v
```
