"""Tests for Topic 01: CLI Task Manager."""

import json
from pathlib import Path
import sys
import tempfile
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from task_manager import (
    Task,
    TaskManager,
    TaskNotFoundError,
    TaskPriority,
    TaskStatus,
)


def test_task_creation():
    task = Task(title="Test Task", description="Testing creation")
    assert task.title == "Test Task"
    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.MEDIUM
    assert len(task.id) == 8


def test_task_serialization():
    task = Task(title="Serialize Me", priority=TaskPriority.HIGH)
    data = task.to_dict()
    assert data["title"] == "Serialize Me"
    assert data["priority"] == "high"
    assert isinstance(data["created_at"], str)

    restored = Task.from_dict(data)
    assert restored.title == task.title
    assert restored.priority == task.priority
    assert restored.id == task.id


def test_task_defensive_deserialization():
    """Test handling of invalid dates, unknown enums, and extra attributes."""
    malformed = {
        "title": "Malformed Attributes",
        "description": "Agent tool injected extra keys",
        "status": "NON_EXISTENT_STATUS",
        "priority": "ULTRA_URGENT",
        "created_at": "invalid-iso-date-string",
        "hallucinated_param": "should_be_ignored",
    }
    task = Task.from_dict(malformed)
    assert task.title == "Malformed Attributes"
    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.MEDIUM
    assert hasattr(task, "created_at")
    assert not hasattr(task, "hallucinated_param")


def test_manager_crud_operations():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "tasks.json"
        manager = TaskManager(storage_path=storage)

        # 1. Add Task
        t1 = manager.add_task("Learn Python", priority=TaskPriority.HIGH)
        t2 = manager.add_task("Learn Git", priority=TaskPriority.LOW)
        assert len(manager.list_tasks()) == 2

        # 2. Get Task
        fetched = manager.get_task(t1.id)
        assert fetched.title == "Learn Python"

        # 3. Update Status
        updated = manager.update_task_status(t1.id, TaskStatus.COMPLETED)
        assert updated.status == TaskStatus.COMPLETED

        # 4. Filter List
        completed = manager.list_tasks(status=TaskStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].id == t1.id

        # 5. Delete Task
        manager.delete_task(t2.id)
        assert len(manager.list_tasks()) == 1

        with pytest.raises(TaskNotFoundError):
            manager.get_task(t2.id)

        # 6. Persistence Check
        manager_reload = TaskManager(storage_path=storage)
        assert len(manager_reload.list_tasks()) == 1
        assert manager_reload.get_task(t1.id).status == TaskStatus.COMPLETED


def test_manager_query_search():
    manager = TaskManager()
    manager.add_task("Build LangGraph agent", description="Multi-agent supervisor pattern")
    manager.add_task("Refactor database queries", description="Use async session")
    manager.add_task("Write unit tests", description="Pytest suite for agents")

    # Search in title
    results_title = manager.list_tasks(query="LangGraph")
    assert len(results_title) == 1
    assert "LangGraph" in results_title[0].title

    # Search in description
    results_desc = manager.list_tasks(query="async session")
    assert len(results_desc) == 1
    assert results_desc[0].title == "Refactor database queries"

    # Case-insensitive search
    results_ci = manager.list_tasks(query="SUPERVISOR")
    assert len(results_ci) == 1


def test_corrupted_json_recovery():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "tasks.json"
        # Write corrupted JSON to disk
        storage.write_text("{corrupt: json content[unclosed", encoding="utf-8")

        # Loading should not crash; it should log error, make backup, and reset
        manager = TaskManager(storage_path=storage)
        assert len(manager.list_tasks()) == 0

        # Verify forensic backup was created
        backup_files = list(Path(tmpdir).glob("tasks.corrupted.*"))
        assert len(backup_files) == 1
        assert "{corrupt" in backup_files[0].read_text(encoding="utf-8")
