"""Tests for Topic 01: CLI Task Manager."""

import sys
import tempfile
from pathlib import Path
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
