"""Topic 01: CLI Task Manager (Starter Template).

Complete each TODO section alongside your AI Assistant.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
import uuid


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskNotFoundError(Exception):
    """Raised when an operation is attempted on a non-existent task."""
    pass


@dataclass
class Task:
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert Task instance to JSON-serializable dictionary."""
        # TODO: Return a dictionary representation with isoformatted datetime string
        raise NotImplementedError("Implement to_dict")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Create a Task instance from a dictionary."""
        # TODO: Parse status and priority enums, convert created_at back to datetime
        raise NotImplementedError("Implement from_dict")


class TaskManager:
    """Manages an in-memory task collection with JSON file persistence."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else None
        self._tasks: dict[str, Task] = {}

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> Task:
        """Add a new task and return it."""
        # TODO: Instantiate Task, store in self._tasks, and return it
        raise NotImplementedError("Implement add_task")

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
    ) -> list[Task]:
        """Return tasks optionally filtered by status and/or priority."""
        # TODO: Filter self._tasks.values() based on provided filters
        raise NotImplementedError("Implement list_tasks")

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task by ID or raise TaskNotFoundError."""
        # TODO: Lookup task in self._tasks or raise TaskNotFoundError(f"Task '{task_id}' not found")
        raise NotImplementedError("Implement get_task")

    def update_task_status(self, task_id: str, new_status: TaskStatus) -> Task:
        """Update the status of an existing task."""
        # TODO: Retrieve task, update status, and return task
        raise NotImplementedError("Implement update_task_status")

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID. Raise TaskNotFoundError if not found."""
        # TODO: Delete task from self._tasks or raise TaskNotFoundError
        raise NotImplementedError("Implement delete_task")

    def save_to_file(self) -> None:
        """Persist all tasks to self.storage_path in JSON format."""
        # TODO: Serialize all tasks to self.storage_path
        raise NotImplementedError("Implement save_to_file")

    def load_from_file(self) -> None:
        """Load tasks from self.storage_path into memory."""
        # TODO: Read JSON from self.storage_path and populate self._tasks
        raise NotImplementedError("Implement load_from_file")


def main() -> None:
    print("Welcome to CLI Task Manager! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
