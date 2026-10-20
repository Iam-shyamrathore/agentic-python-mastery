"""Tests for Topic 05: SQL & Database Connections."""

import sys
import tempfile
from pathlib import Path
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from database import DatabaseService
from models import TaskModel


@pytest.fixture
def db_service():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_tasks.db"
        service = DatabaseService(db_url=f"sqlite:///{db_path}")
        yield service


def test_add_and_get_task(db_service):
    task = db_service.add_task(title="Deploy Model", description="Deploy onto FastAPI", priority="high")
    assert task.id is not None
    assert task.title == "Deploy Model"
    assert task.status == "pending"

    fetched = db_service.get_task(task.id)
    assert fetched is not None
    assert fetched.title == "Deploy Model"


def test_list_and_filter_tasks(db_service):
    t1 = db_service.add_task(title="Task A")
    t2 = db_service.add_task(title="Task B")
    db_service.update_task_status(t1.id, "completed")

    all_tasks = db_service.list_tasks()
    assert len(all_tasks) == 2

    completed_tasks = db_service.list_tasks(status="completed")
    assert len(completed_tasks) == 1
    assert completed_tasks[0].id == t1.id


def test_update_and_delete_task(db_service):
    task = db_service.add_task(title="Temporary Task")
    updated = db_service.update_task_status(task.id, "in_progress")
    assert updated.status == "in_progress"

    deleted = db_service.delete_task(task.id)
    assert deleted is True

    assert db_service.get_task(task.id) is None
