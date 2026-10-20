"""Tests for Topic 05: SQL & Database Connections.

Validates SQLAlchemy 2.0 models, connection pooling configuration,
transactional safety, indexing, and pagination helpers.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import pytest
from sqlalchemy.pool import QueuePool

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from database import DatabaseService
from models import TaskModel


@pytest.fixture
def db_service():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_tasks.db"
        service = DatabaseService(
            db_url=f"sqlite:///{db_path}",
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
            pool_pre_ping=True,
        )
        yield service


def test_add_and_get_task(db_service):
    task = db_service.add_task(title="Deploy Model", description="Deploy onto FastAPI", priority="high")
    assert task.id is not None
    assert task.title == "Deploy Model"
    assert task.status == "pending"

    fetched = db_service.get_task(task.id)
    assert fetched is not None
    assert fetched.title == "Deploy Model"
    assert fetched.description == "Deploy onto FastAPI"
    assert fetched.priority == "high"


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
    # Deleting non-existent should return False
    assert db_service.delete_task(task.id) is False


def test_pagination_limit_and_offset(db_service):
    for i in range(5):
        db_service.add_task(title=f"Task {i + 1}")

    # Limit 2, Offset 0
    page1 = db_service.list_tasks(limit=2, offset=0)
    assert len(page1) == 2

    # Limit 2, Offset 2
    page2 = db_service.list_tasks(limit=2, offset=2)
    assert len(page2) == 2

    # Ensure pages do not overlap
    page1_ids = {t.id for t in page1}
    page2_ids = {t.id for t in page2}
    assert page1_ids.isdisjoint(page2_ids)

    # Offset beyond row count
    empty_page = db_service.list_tasks(limit=2, offset=10)
    assert len(empty_page) == 0


def test_list_tasks_paginated_helper(db_service):
    for i in range(7):
        db_service.add_task(title=f"Queued Task {i + 1}")

    items, total = db_service.list_tasks_paginated(limit=3, offset=0)
    assert len(items) == 3
    assert total == 7

    # Page 2
    items_p2, total_p2 = db_service.list_tasks_paginated(limit=3, offset=3)
    assert len(items_p2) == 3
    assert total_p2 == 7

    # Page 3 (remainder)
    items_p3, total_p3 = db_service.list_tasks_paginated(limit=3, offset=6)
    assert len(items_p3) == 1
    assert total_p3 == 7


def test_count_tasks(db_service):
    t1 = db_service.add_task(title="Task 1", priority="high")
    t2 = db_service.add_task(title="Task 2", priority="low")
    t3 = db_service.add_task(title="Task 3", priority="high")
    db_service.update_task_status(t3.id, "completed")

    assert db_service.count_tasks() == 3
    assert db_service.count_tasks(status="pending") == 2
    assert db_service.count_tasks(status="completed") == 1
    assert db_service.count_tasks(priority="high") == 2
    assert db_service.count_tasks(priority="low") == 1


def test_connection_pool_configuration(db_service):
    """Verify that QueuePool parameters are properly assigned to the engine."""
    pool = db_service.engine.pool
    assert isinstance(pool, QueuePool)
    assert pool._pre_ping is True
    assert pool._recycle == 1800
    assert pool.size() == 5
    assert pool._max_overflow == 10


def test_transaction_rollback_on_failure(db_service):
    """Verify that exceptions inside session_scope cleanly roll back transactions."""
    initial_count = db_service.count_tasks()

    with pytest.raises(RuntimeError):
        with db_service.session_scope() as session:
            task = TaskModel(title="Doomed Task", status="pending")
            session.add(task)
            session.flush()
            # Force an error before exiting context
            raise RuntimeError("Simulated agent worker crash during write")

    # Verify task was not committed
    assert db_service.count_tasks() == initial_count


def test_add_task_validation(db_service):
    """Verify defensive validation prevents blank/whitespace titles."""
    with pytest.raises(ValueError, match="Task title cannot be empty"):
        db_service.add_task(title="   ")
