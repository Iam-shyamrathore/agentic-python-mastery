"""Topic 01: CLI Task Manager (Complete Reference Solution).

Production-grade implementation demonstrating modern Python type hints,
dataclasses, enums, defensive error handling, and JSON persistence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import sys
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
        data = asdict(self)
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Create a Task instance from a dictionary."""
        data_copy = data.copy()
        if "status" in data_copy and isinstance(data_copy["status"], str):
            data_copy["status"] = TaskStatus(data_copy["status"])
        if "priority" in data_copy and isinstance(data_copy["priority"], str):
            data_copy["priority"] = TaskPriority(data_copy["priority"])
        if "created_at" in data_copy and isinstance(data_copy["created_at"], str):
            data_copy["created_at"] = datetime.fromisoformat(data_copy["created_at"])
        return cls(**data_copy)


class TaskManager:
    """Manages an in-memory task collection with JSON file persistence."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
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
        """Add a new task and return it."""
        if not title.strip():
            raise ValueError("Task title cannot be empty.")
        task = Task(title=title.strip(), description=description.strip(), priority=priority)
        self._tasks[task.id] = task
        if self.storage_path:
            self.save_to_file()
        return task

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
    ) -> list[Task]:
        """Return tasks optionally filtered by status and/or priority."""
        results = list(self._tasks.values())
        if status:
            results = [t for t in results if t.status == status]
        if priority:
            results = [t for t in results if t.priority == priority]
        return sorted(results, key=lambda t: t.created_at, reverse=True)

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task by ID or raise TaskNotFoundError."""
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task with ID '{task_id}' does not exist.")
        return self._tasks[task_id]

    def update_task_status(self, task_id: str, new_status: TaskStatus) -> Task:
        """Update the status of an existing task."""
        task = self.get_task(task_id)
        task.status = new_status
        if self.storage_path:
            self.save_to_file()
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID. Raise TaskNotFoundError if not found."""
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task with ID '{task_id}' does not exist.")
        del self._tasks[task_id]
        if self.storage_path:
            self.save_to_file()
        return True

    def save_to_file(self) -> None:
        """Persist all tasks to self.storage_path in JSON format."""
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [task.to_dict() for task in self._tasks.values()]
        temp_path = self.storage_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2)
        temp_path.replace(self.storage_path)

    def load_from_file(self) -> None:
        """Load tasks from self.storage_path into memory."""
        if not self.storage_path or not self.storage_path.exists():
            return
        with open(self.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._tasks = {item["id"]: Task.from_dict(item) for item in data}


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI Task Manager for AI Engineers")
    parser.add_argument("--storage", default="tasks.json", help="Path to JSON storage file")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Add task
    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("title", help="Task title")
    add_parser.add_argument("--desc", default="", help="Task description")
    add_parser.add_argument("--priority", choices=["low", "medium", "high"], default="medium")

    # List tasks
    list_parser = subparsers.add_parser("list", help="List all tasks")
    list_parser.add_argument("--status", choices=["pending", "in_progress", "completed"], default=None)
    list_parser.add_argument("--priority", choices=["low", "medium", "high"], default=None)

    # Complete task
    complete_parser = subparsers.add_parser("complete", help="Mark task completed")
    complete_parser.add_argument("id", help="Task ID to complete")

    # Delete task
    delete_parser = subparsers.add_parser("delete", help="Delete a task")
    delete_parser.add_argument("id", help="Task ID to delete")

    args = parser.parse_args()
    manager = TaskManager(storage_path=args.storage)

    if args.command == "add":
        task = manager.add_task(args.title, args.desc, TaskPriority(args.priority))
        print(f"✅ Added Task [{task.id}]: {task.title} (Priority: {task.priority.value})")

    elif args.command == "list":
        status_filter = TaskStatus(args.status) if args.status else None
        priority_filter = TaskPriority(args.priority) if args.priority else None
        tasks = manager.list_tasks(status=status_filter, priority=priority_filter)
        if not tasks:
            print("📭 No tasks found matching criteria.")
        else:
            print(f"\n📋 Task List ({len(tasks)} total):")
            print("-" * 65)
            for t in tasks:
                status_icon = "🟢" if t.status == TaskStatus.COMPLETED else ("🟡" if t.status == TaskStatus.IN_PROGRESS else "⚪")
                print(f"{status_icon} [{t.id}] {t.title} | {t.status.value.upper()} | Pri: {t.priority.value}")
            print("-" * 65)

    elif args.command == "complete":
        try:
            task = manager.update_task_status(args.id, TaskStatus.COMPLETED)
            print(f"🎉 Task [{task.id}] marked as COMPLETED!")
        except TaskNotFoundError as e:
            print(f"❌ Error: {e}", file=sys.stderr)

    elif args.command == "delete":
        try:
            manager.delete_task(args.id)
            print(f"🗑️ Task [{args.id}] deleted successfully.")
        except TaskNotFoundError as e:
            print(f"❌ Error: {e}", file=sys.stderr)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
