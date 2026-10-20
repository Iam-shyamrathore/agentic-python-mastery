"""Topic 01: CLI Task Manager (Complete Reference Solution).

Production-grade implementation demonstrating modern Python type hints,
dataclasses, enums, defensive error handling, atomic JSON persistence,
and rich terminal presentation for AI agent pipelines.

Why this architecture matters in AI Engineering:
------------------------------------------------
1. Structured Data Models (Dataclasses & Enums):
   AI agents communicate using structured tool calls and JSON schemas. Free-form
   dictionaries lead to silent key errors, type drift, and subtle bugs during LLM
   output parsing. Dataclasses enforce strict attribute types, default factories,
   and bidirectional serialization to/from JSON.

2. Enums for Bounded States:
   LLMs frequently hallucinate near-synonyms (e.g., "done" instead of "completed",
   "urgent" instead of "high"). Wrapping statuses and priorities in string Enums
   (`str, Enum`) provides strict boundary validation while remaining directly
   JSON-serializable.

3. Atomic File Writes (`temp_path.replace()`):
   Agent loops frequently execute concurrently or run in containerized environments
   subject to sudden OOM kills, timeouts, or spot-instance termination. Directly writing
   to `tasks.json` can leave a truncated 0-byte or partially written corrupted file.
   Writing to a unique temporary file and performing an atomic filesystem replace ensures
   that the file on disk is either fully updated or completely untouched.

4. Corrupted State Recovery:
   If an agent crashes or disk corruption occurs, crashing the entire service is
   unacceptable. Detecting `JSONDecodeError`, creating an isolated forensic backup
   (`.corrupted`), and failing safely keeps production agent systems resilient.
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

# Configure structured standard logging
logger = logging.getLogger("agentic_task_manager")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class TaskStatus(str, Enum):
    """Enumeration of allowed lifecycle states for a task.
    
    Subclassing `str` enables seamless JSON serialization and case comparisons
    while enforcing strict membership validation.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskPriority(str, Enum):
    """Enumeration of priority tiers for execution scheduling."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskManagerError(Exception):
    """Base exception for all domain-level task management errors."""
    pass


class TaskNotFoundError(TaskManagerError):
    """Raised when an operation references a non-existent task ID."""
    pass


class CorruptedStorageError(TaskManagerError):
    """Raised when task storage file exists but contains unparseable data."""
    pass


@dataclass
class Task:
    """Represents an atomic unit of work within an agent pipeline.

    Attributes:
        title: Short descriptive headline for the task.
        description: Detailed context, execution notes, or tool instructions.
        status: Current execution state from `TaskStatus`.
        priority: Urgency tier from `TaskPriority`.
        id: Unique 8-character identifier generated via UUID4.
        created_at: UTC timestamp capturing exact task creation time.
    """
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert Task instance to a clean JSON-serializable dictionary.
        
        Why this pattern is preferred in AI pipelines:
        Datetime objects and Enum instances cannot be passed directly into
        `json.dump()` without custom encoders. Converting `created_at` to an ISO 8601
        string and enums to `.value` ensures compatibility across REST APIs, LangChain
        tool outputs, and disk storage.
        """
        data = asdict(self)
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Create a Task instance defensively from a dictionary.
        
        Handles defensive deserialization:
        - Coerces string values into typed `TaskStatus` and `TaskPriority` enums.
        - Parses ISO 8601 timestamps with fallback to current UTC time if corrupted.
        - Ignores extraneous fields LLMs might inject into tool arguments.
        """
        data_copy = data.copy()
        
        # Defensive Enum Coercion
        if "status" in data_copy and isinstance(data_copy["status"], str):
            try:
                data_copy["status"] = TaskStatus(data_copy["status"].lower())
            except ValueError:
                logger.warning(
                    "Invalid status '%s' encountered. Defaulting to PENDING.",
                    data_copy["status"],
                )
                data_copy["status"] = TaskStatus.PENDING

        if "priority" in data_copy and isinstance(data_copy["priority"], str):
            try:
                data_copy["priority"] = TaskPriority(data_copy["priority"].lower())
            except ValueError:
                logger.warning(
                    "Invalid priority '%s' encountered. Defaulting to MEDIUM.",
                    data_copy["priority"],
                )
                data_copy["priority"] = TaskPriority.MEDIUM

        # Defensive Datetime Parsing
        if "created_at" in data_copy:
            if isinstance(data_copy["created_at"], str):
                try:
                    data_copy["created_at"] = datetime.fromisoformat(data_copy["created_at"])
                except ValueError:
                    logger.warning(
                        "Malformed ISO datetime '%s'. Resetting to UTC now.",
                        data_copy["created_at"],
                    )
                    data_copy["created_at"] = datetime.now(timezone.utc)
            elif not isinstance(data_copy["created_at"], datetime):
                data_copy["created_at"] = datetime.now(timezone.utc)

        # Filter unexpected keys to prevent TypeError on instantiating dataclass
        valid_fields = cls.__dataclass_fields__.keys()
        sanitized = {k: v for k, v in data_copy.items() if k in valid_fields}
        return cls(**sanitized)


class TaskManager:
    """Manages an in-memory task collection with atomic JSON file persistence."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        """Initialize the task manager.
        
        Args:
            storage_path: Optional path to a JSON file for persisting tasks.
                          If provided, existing tasks are automatically loaded.
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
        """Add a new task to the collection and persist changes.
        
        Args:
            title: Title of the task (must not be whitespace-only).
            description: Optional detailed description.
            priority: Task priority tier (`TaskPriority`).
            
        Returns:
            The created `Task` instance.
            
        Raises:
            ValueError: If `title` is empty or only whitespace.
        """
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title cannot be empty.")
            
        task = Task(
            title=clean_title,
            description=description.strip(),
            priority=priority,
        )
        self._tasks[task.id] = task
        logger.debug("Added task %s: '%s'", task.id, task.title)
        
        if self.storage_path:
            self.save_to_file()
        return task

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        query: str | None = None,
    ) -> list[Task]:
        """Return tasks matching optional filters, sorted by creation date descending.
        
        Args:
            status: Optional status filter.
            priority: Optional priority filter.
            query: Optional case-insensitive substring search across title and description.
            
        Returns:
            List of matching `Task` instances.
        """
        results = list(self._tasks.values())
        if status:
            results = [t for t in results if t.status == status]
        if priority:
            results = [t for t in results if t.priority == priority]
        if query:
            clean_query = query.strip().lower()
            results = [
                t for t in results
                if clean_query in t.title.lower() or clean_query in t.description.lower()
            ]
        return sorted(results, key=lambda t: t.created_at, reverse=True)

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task by its unique ID.
        
        Args:
            task_id: Unique task identifier.
            
        Returns:
            The requested `Task` instance.
            
        Raises:
            TaskNotFoundError: If the ID does not exist in memory.
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task with ID '{task_id}' does not exist.")
        return self._tasks[task_id]

    def update_task_status(self, task_id: str, new_status: TaskStatus) -> Task:
        """Update the lifecycle status of an existing task.
        
        Args:
            task_id: Unique task identifier.
            new_status: New `TaskStatus` value.
            
        Returns:
            The updated `Task` instance.
            
        Raises:
            TaskNotFoundError: If task ID does not exist.
        """
        task = self.get_task(task_id)
        task.status = new_status
        logger.debug("Updated task %s status to %s", task_id, new_status.value)
        if self.storage_path:
            self.save_to_file()
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID.
        
        Args:
            task_id: Unique task identifier.
            
        Returns:
            True if deletion was successful.
            
        Raises:
            TaskNotFoundError: If task ID does not exist.
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task with ID '{task_id}' does not exist.")
        del self._tasks[task_id]
        logger.debug("Deleted task %s", task_id)
        if self.storage_path:
            self.save_to_file()
        return True

    def save_to_file(self) -> None:
        """Persist tasks atomically to `self.storage_path` in JSON format.
        
        Production Implementation Detail:
        Directly calling `open(self.storage_path, 'w')` is prone to corruption if
        the process is interrupted mid-write. We serialize into a unique temporary
        file in the target directory and rename it using `Path.replace()`, which is
        an atomic syscall on POSIX filesystems and Windows.
        """
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [task.to_dict() for task in self._tasks.values()]
        
        # Use a unique suffix to prevent collisions with concurrent threads/subprocesses
        temp_path = self.storage_path.with_suffix(f".tmp.{uuid.uuid4().hex[:6]}")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2, ensure_ascii=False)
            temp_path.replace(self.storage_path)
            logger.debug("Atomic write completed: %s", self.storage_path)
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    def load_from_file(self) -> None:
        """Load tasks from `self.storage_path` with corrupted file recovery.
        
        Production Error Recovery:
        If `tasks.json` has been corrupted (e.g. invalid JSON from an external edit
        or abrupt power failure), we preserve the bad file as `.corrupted.<timestamp>`
        to allow post-mortem debugging, log an error, and initialize a clean task store.
        """
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    self._tasks = {}
                    return
                data = json.loads(content)

            if not isinstance(data, list):
                raise ValueError("Expected JSON array of task objects.")

            self._tasks = {item["id"]: Task.from_dict(item) for item in data}
            logger.info("Successfully loaded %d tasks from %s", len(self._tasks), self.storage_path)

        except (json.JSONDecodeError, ValueError) as err:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            corrupt_backup = self.storage_path.with_suffix(f".corrupted.{timestamp}")
            try:
                shutil.copy2(self.storage_path, corrupt_backup)
                logger.error(
                    "Corrupted task storage at '%s' (%s). Created recovery backup at '%s'.",
                    self.storage_path,
                    err,
                    corrupt_backup,
                )
            except OSError as copy_err:
                logger.error("Failed to back up corrupted storage: %s", copy_err)

            self._tasks = {}


def render_rich_tasks(tasks: list[Task]) -> None:
    """Render task collection using Rich library tables if available."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f"📋 Task List ({len(tasks)} items)", show_lines=False, header_style="bold magenta")
        table.add_column("Status", justify="center", width=6)
        table.add_column("ID", style="dim", width=10)
        table.add_column("Title", style="bold white", min_width=25)
        table.add_column("Priority", justify="center", width=10)
        table.add_column("Created", style="dim", width=16)

        for t in tasks:
            if t.status == TaskStatus.COMPLETED:
                status_str = "[green]✔ Done[/green]"
            elif t.status == TaskStatus.IN_PROGRESS:
                status_str = "[yellow]⏳ Prog[/yellow]"
            else:
                status_str = "[blue]⚪ Pend[/blue]"

            pri_color = {"high": "red", "medium": "yellow", "low": "cyan"}.get(t.priority.value, "white")
            pri_str = f"[{pri_color}]{t.priority.value.upper()}[/{pri_color}]"
            date_str = t.created_at.strftime("%Y-%m-%d %H:%M")

            table.add_row(status_str, t.id, t.title, pri_str, date_str)

        console.print(table)
    except ImportError:
        # Fallback to standard console formatting
        print(f"\n📋 Task List ({len(tasks)} total):")
        print("-" * 65)
        for t in tasks:
            status_icon = "🟢" if t.status == TaskStatus.COMPLETED else ("🟡" if t.status == TaskStatus.IN_PROGRESS else "⚪")
            print(f"{status_icon} [{t.id}] {t.title} | {t.status.value.upper()} | Pri: {t.priority.value}")
        print("-" * 65)


def main() -> None:
    """CLI entrypoint for interactive task management."""
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
    list_parser.add_argument("--query", "-q", default=None, help="Filter tasks by text query")

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
        try:
            from rich.console import Console
            Console().print(f"[bold green]✔ Added Task[/bold green] [{task.id}]: [white]{task.title}[/white] (Priority: [yellow]{task.priority.value}[/yellow])")
        except ImportError:
            print(f"✅ Added Task [{task.id}]: {task.title} (Priority: {task.priority.value})")

    elif args.command == "list":
        status_filter = TaskStatus(args.status) if args.status else None
        priority_filter = TaskPriority(args.priority) if args.priority else None
        tasks = manager.list_tasks(status=status_filter, priority=priority_filter, query=args.query)
        if not tasks:
            print("📭 No tasks found matching criteria.")
        else:
            render_rich_tasks(tasks)

    elif args.command == "complete":
        try:
            task = manager.update_task_status(args.id, TaskStatus.COMPLETED)
            try:
                from rich.console import Console
                Console().print(f"[bold green]🎉 Task [{task.id}] marked as COMPLETED![/bold green]")
            except ImportError:
                print(f"🎉 Task [{task.id}] marked as COMPLETED!")
        except TaskNotFoundError as e:
            logger.error("Operation failed: %s", e)
            print(f"❌ Error: {e}", file=sys.stderr)

    elif args.command == "delete":
        try:
            manager.delete_task(args.id)
            try:
                from rich.console import Console
                Console().print(f"[bold red]🗑️ Task [{args.id}] deleted successfully.[/bold red]")
            except ImportError:
                print(f"🗑️ Task [{args.id}] deleted successfully.")
        except TaskNotFoundError as e:
            logger.error("Operation failed: %s", e)
            print(f"❌ Error: {e}", file=sys.stderr)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
