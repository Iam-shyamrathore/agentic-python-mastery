"""Topic 01: CLI Task Manager (Starter Scaffolding).

Production-Grade Instructional Template:
Follow the step-by-step TODO milestones alongside your AI Assistant to build
a resilient, typed task manager that handles state storage, atomic writes,
and corrupted file recovery.

AI Engineering Rationale:
-------------------------
Agentic systems frequently manipulate structured state files (e.g., plan steps,
tool execution logs, memory records). A naive implementation using untyped dictionaries
and non-atomic file writes will fail catastrophically in production when:
- An LLM generates invalid status strings.
- Process crashes or OOM events truncate state files during file writes.
- Malformed timestamps cause downstream sorting algorithms to crash.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from pathlib import Path
import shutil
import sys
from typing import Any
import uuid

# Configure module-level logging for tracing agent state transitions
logger = logging.getLogger("task_manager")


class TaskStatus(str, Enum):
    """Lifecycle status states for tasks.
    
    Why inherit from `str` and `Enum`?
    Subclassing `str` ensures automatic string compatibility with JSON serializers
    and prevents LLM hallucination of arbitrary status values (e.g. 'done', 'finished').
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskPriority(str, Enum):
    """Urgency levels for scheduling and filtering."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskNotFoundError(Exception):
    """Raised when an operation is attempted on a non-existent task ID."""
    pass


class CorruptedStorageError(Exception):
    """Raised when task storage file exists but cannot be parsed as valid JSON."""
    pass


@dataclass
class Task:
    """Atomic unit of work in an agent task queue.

    Fields:
        title (str): Concise label for the task.
        description (str): Detailed context, instructions, or payload.
        status (TaskStatus): Current state, defaults to PENDING.
        priority (TaskPriority): Urgency tier, defaults to MEDIUM.
        id (str): Short unique identifier (8 hex characters from UUID4).
        created_at (datetime): UTC timestamp of task creation.
    """
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert Task instance to a JSON-serializable dictionary.
        
        Step-by-step Implementation Guide:
        1. Use `asdict(self)` to convert the dataclass fields to a standard dictionary.
        2. Replace `status` with its string value: `self.status.value`.
        3. Replace `priority` with its string value: `self.priority.value`.
        4. Replace `created_at` with its ISO 8601 formatted string: `self.created_at.isoformat()`.
        5. Return the modified dictionary.
        
        Edge Cases to Consider:
        - `datetime` objects are NOT natively JSON-serializable. Using `.isoformat()`
          preserves timezone offsets and microsecond precision.
        """
        # TODO: Implement to_dict following the steps above
        raise NotImplementedError("Implement to_dict")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Create a Task instance from a serialized dictionary defensively.
        
        Step-by-step Implementation Guide:
        1. Make a shallow copy of `data` (avoid mutating caller's dictionary).
        2. Parse `status`: If string, wrap in `TaskStatus(data_copy['status'])`.
           Add a try/except ValueError block: if invalid, fallback to `TaskStatus.PENDING`.
        3. Parse `priority`: If string, wrap in `TaskPriority(data_copy['priority'])`.
           If invalid, fallback to `TaskPriority.MEDIUM`.
        4. Parse `created_at`: If string, parse with `datetime.fromisoformat(...)`.
           If malformed or missing, fallback to `datetime.now(timezone.utc)`.
        5. Filter out any unexpected keys that do not belong to `cls.__dataclass_fields__`
           (this prevents crashes if an LLM injected extra keys into the dictionary).
        6. Return `cls(**sanitized_data)`.
        """
        # TODO: Implement defensive from_dict following the steps above
        raise NotImplementedError("Implement from_dict")


class TaskManager:
    """Manages an in-memory task collection with atomic JSON file persistence."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        """Initialize the task manager.
        
        Args:
            storage_path: Optional file path for storing tasks. If path exists,
                          automatically invoke `self.load_from_file()`.
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self._tasks: dict[str, Task] = {}
        if self.storage_path and self.storage_path.exists():
            self.load_from_file()

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> Task:
        """Add a new task and persist to disk if `storage_path` is configured.
        
        Implementation Hints:
        1. Strip whitespace from `title`. If empty, raise `ValueError("Task title cannot be empty.")`.
        2. Instantiate `Task(title=title, description=description, priority=priority)`.
        3. Insert into `self._tasks[task.id] = task`.
        4. If `self.storage_path` is not None, call `self.save_to_file()`.
        5. Return the created `task`.
        """
        # TODO: Implement add_task
        raise NotImplementedError("Implement add_task")

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        query: str | None = None,
    ) -> list[Task]:
        """Return tasks filtered by status, priority, and text search, sorted newest first.
        
        Implementation Hints:
        1. Start with `results = list(self._tasks.values())`.
        2. If `status` is provided, filter: `[t for t in results if t.status == status]`.
        3. If `priority` is provided, filter: `[t for t in results if t.priority == priority]`.
        4. If `query` is provided, perform case-insensitive search across title & description:
           `[t for t in results if query.lower() in t.title.lower() or query.lower() in t.description.lower()]`.
        5. Return `sorted(results, key=lambda t: t.created_at, reverse=True)`.
        """
        # TODO: Implement list_tasks with filtering and search
        raise NotImplementedError("Implement list_tasks")

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task by ID or raise TaskNotFoundError.
        
        Implementation Hints:
        - Check if `task_id` is in `self._tasks`.
        - If not, raise `TaskNotFoundError(f"Task with ID '{task_id}' does not exist.")`.
        - Return `self._tasks[task_id]`.
        """
        # TODO: Implement get_task
        raise NotImplementedError("Implement get_task")

    def update_task_status(self, task_id: str, new_status: TaskStatus) -> Task:
        """Update task lifecycle status and persist changes.
        
        Implementation Hints:
        1. Retrieve the task with `self.get_task(task_id)` (handles TaskNotFoundError).
        2. Set `task.status = new_status`.
        3. If `self.storage_path`, call `self.save_to_file()`.
        4. Return the updated `task`.
        """
        # TODO: Implement update_task_status
        raise NotImplementedError("Implement update_task_status")

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID. Raise TaskNotFoundError if not found.
        
        Implementation Hints:
        1. Validate `task_id` in `self._tasks`.
        2. Delete entry `del self._tasks[task_id]`.
        3. If `self.storage_path`, call `self.save_to_file()`.
        4. Return True.
        """
        # TODO: Implement delete_task
        raise NotImplementedError("Implement delete_task")

    def save_to_file(self) -> None:
        """Persist all tasks atomically to `self.storage_path` in JSON format.
        
        Why Atomic Writes Matter:
        If you write directly with `open(self.storage_path, 'w')`, an unexpected crash
        (OOM kill, power loss, Ctrl+C) leaves an empty or corrupt JSON file.
        
        Implementation Hints:
        1. If `self.storage_path` is None, return immediately.
        2. Ensure parent directory exists: `self.storage_path.parent.mkdir(parents=True, exist_ok=True)`.
        3. Serialize tasks: `serialized = [t.to_dict() for t in self._tasks.values()]`.
        4. Create a temporary path in the SAME directory: `temp_path = self.storage_path.with_suffix(".tmp")`.
        5. Write JSON to `temp_path` using UTF-8 encoding.
        6. Atomically replace: `temp_path.replace(self.storage_path)`.
        """
        # TODO: Implement atomic save_to_file
        raise NotImplementedError("Implement save_to_file")

    def load_from_file(self) -> None:
        """Load tasks from `self.storage_path` with corrupted file recovery.
        
        Implementation Hints:
        1. If `self.storage_path` is None or does not exist, return immediately.
        2. Open file and read content. If empty string, set `self._tasks = {}` and return.
        3. In a `try...except (json.JSONDecodeError, ValueError)` block:
           - Parse `data = json.loads(content)`.
           - Repopulate `self._tasks = {item['id']: Task.from_dict(item) for item in data}`.
        4. In the `except` block:
           - Copy corrupted file to a backup path: `self.storage_path.with_suffix('.corrupted.<timestamp>')`.
           - Log an error warning about file corruption.
           - Reset `self._tasks = {}` to avoid permanent crash loops.
        """
        # TODO: Implement load_from_file with forensic recovery
        raise NotImplementedError("Implement load_from_file")


def main() -> None:
    """CLI entrypoint for interactive task manager."""
    print("Welcome to CLI Task Manager! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
