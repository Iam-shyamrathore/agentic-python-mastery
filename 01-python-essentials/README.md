# 🐍 Topic 01: Python Essentials for AI Engineers

> **Master the fundamental Python idioms, data structures, type hints, dataclasses, defensive error handling, and serialization patterns essential for mission-critical AI systems.**

---

## 🎯 Why This Topic Matters in AI Engineering

AI Engineering is NOT just calling `model.generate()`. Real-world AI applications require:
- Parsing messy, unpredictably structured JSON responses from LLMs.
- Strict data contracts using Type Hints, Dataclasses, and Enums to constrain agent state.
- Defensive exception handling when external model APIs fail, throttle, or hallucinate invalid schemas.
- Safe file persistence with atomic writes so spot instances and container restarts don't corrupt state.
- Efficient memory management when maintaining long conversation histories and tool traces.

---

## 💥 Production War Stories & Hard-Learned Lessons

### 💥 War Story 1: The Midnight 0-Byte State File Disaster
> **The Scenario:** An autonomous coding agent was deployed on AWS EC2 Spot instances, executing long 4-hour batch evaluation runs. Every time a sub-task completed, the agent serialized its state:
> ```python
> # ❌ NAIVE IMPLEMENTATION:
> with open("agent_state.json", "w") as f:
>     json.dump(state, f)
> ```
> **The Incident:** AWS spot instances receive a 2-minute interruption notice before termination. During an instance reclamation, the container was killed mid-write while writing a 45 MB state file. When the new container spun up, `agent_state.json` was a truncated, 0-byte invalid file. Because there was no atomic swap or backup, 4 hours of evaluation state were permanently erased.
> 
> **The Fix:** Always write to a unique temporary file (`temp_path = path.with_suffix(f".tmp.{uuid4().hex[:6]}")`) and call `temp_path.replace(path)`. The POSIX `rename` syscall is atomic—either the old file remains or the new file completely replaces it, never leaving a corrupted half-written file.

---

### 💥 War Story 2: The Hallucinated Enum Infinite Loop
> **The Scenario:** A support triaging agent used plain string statuses:
> ```python
> if task["status"] == "completed":
>     archive_ticket(task)
> ```
> **The Incident:** After switching models from GPT-4o to a quantized local model, the model occasionally returned `"status": "finished"` or `"status": "done"`. The system didn't raise an error; instead, the `if` check silently evaluated to `False`. The orchestrator assumed the ticket was still pending and re-queued it for processing, spamming the customer with 34 duplicate resolution emails overnight.
> 
> **The Fix:** Enforce Python `Enum` with subclassed `str` (`class TaskStatus(str, Enum)`). Validate all incoming model outputs against the enum immediately upon ingestion, rejecting or normalizing invalid states before business logic runs.

---

### 💥 War Story 3: The 100k-Step Memory Leak in Multi-Agent Swarms
> **The Scenario:** An enterprise researcher swarm tracked intermediate reasoning steps across 50 parallel agents using standard Python dictionaries (`{"role": "assistant", "tokens": [...], ...}`).
> 
> **The Incident:** Standard Python `dict` instances incur significant overhead (~232 bytes base per dict + string keys). When 50 agents logged 2,000 reasoning steps each with metadata, memory climbed past 12 GB, triggering container OOM (Out-Of-Memory) kills.
> 
> **The Fix:** Replace generic dicts with `@dataclass(slots=True)`:
> ```python
> @dataclass(slots=True)
> class StepRecord:
>     step_id: str
>     action: str
>     observation: str
> ```
> Using `slots=True` eliminates the per-instance `__dict__`, reducing memory footprint by **up to 60%** and speeding up attribute access.

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

@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert dataclass instance to a clean JSON-serializable dict."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatMessage":
        """Defensively instantiate directly from a serialized dictionary."""
        data_copy = data.copy()
        if "created_at" in data_copy and isinstance(data_copy["created_at"], str):
            try:
                data_copy["created_at"] = datetime.fromisoformat(data_copy["created_at"])
            except ValueError:
                data_copy["created_at"] = datetime.now(timezone.utc)
        # Drop unrecognized keys injected by hallucinating LLMs
        valid_keys = cls.__dataclass_fields__.keys()
        sanitized = {k: v for k, v in data_copy.items() if k in valid_keys}
        return cls(**sanitized)
```

---

### 3. Serialization Gotchas to Watch For

1. **`datetime.utcnow()` is Deprecated (Python 3.12+)**:
   Never use `datetime.utcnow()`; it returns a naive datetime without timezone offset, causing silent 5-hour shifts when serialized alongside UTC offsets. Always use `datetime.now(timezone.utc)`.
2. **JSON Cannot Serialize Non-String Keys**:
   If your dictionary has tuple keys (e.g. `{(source, target): weight}` in graph agents), `json.dump()` raises a `TypeError`. Serialize tuple keys to strings (e.g. `f"{source}->{target}"`).
3. **Pydantic vs Dataclasses**:
   Use dataclasses for lightweight internal agent state loops where sub-microsecond instantiation speed matters. Use Pydantic at the network boundary (FastAPI, LLM structured outputs) where runtime data coercion and validation are required.

---

### 4. Defensive Error Handling & Custom Exceptions

LLM calls, token parsing, and network responses fail frequently. Never catch generic `Exception` blindly. Always create domain-specific exceptions.

```python
class AgenticBaseError(Exception):
    """Base exception for all domain errors."""
    pass

class TaskNotFoundError(AgenticBaseError):
    def __init__(self, task_id: str):
        super().__init__(f"Task with ID '{task_id}' was not found in storage.")
        self.task_id = task_id

class CorruptedStorageError(AgenticBaseError):
    pass

# Safe execution pattern
try:
    raise TaskNotFoundError("task_999")
except TaskNotFoundError as exc:
    logger.warning("Handled domain error: %s", exc)
except AgenticBaseError as exc:
    logger.error("Domain error occurred: %s", exc)
except Exception as exc:
    logger.critical("Unexpected system error: %s", exc, exc_info=True)
```

---

## 🛠️ The Hands-on Project: CLI Task Manager

In this module, you will build a robust, modular Command Line Interface (CLI) Task Manager featuring:
- Typed data models (`Task`, `TaskStatus`, `TaskPriority`)
- Full CRUD operations (Create, Read, Update, Delete)
- Search across titles and descriptions
- Atomic file persistence (`temp_path.replace()`) preventing 0-byte corruptions
- Corrupted JSON recovery with forensic timestamped backups
- Rich terminal UI tables with fallback formatting

### Directory Layout
- `starter/task_manager.py` — Your workspace. Follow the `TODO` blocks!
- `solution/task_manager.py` — Complete, reference implementation.
- `tests/test_task_manager.py` — Automated verification tests.

### Running the Tests
```bash
pytest 01-python-essentials/tests/test_task_manager.py -v
```
