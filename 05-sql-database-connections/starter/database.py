"""Topic 05: Database Service & CRUD Layer (Starter Template).

Complete each TODO section alongside your AI Assistant.
"""

from __future__ import annotations

from typing import Sequence
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, TaskModel


class DatabaseService:
    def __init__(self, db_url: str = "sqlite:///./tasks.db") -> None:
        self.engine = create_engine(db_url, echo=False)
        self.SessionFactory = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def add_task(self, title: str, description: str = "", priority: str = "medium") -> TaskModel:
        """Create and persist a new task."""
        # TODO: Implement transactional insert
        raise NotImplementedError("Implement add_task")

    def list_tasks(self, status: str | None = None) -> Sequence[TaskModel]:
        """List tasks with optional status filter."""
        # TODO: Implement select query with scalars().all()
        raise NotImplementedError("Implement list_tasks")

    def get_task(self, task_id: str) -> TaskModel | None:
        """Get task by ID."""
        # TODO: Implement select by ID
        raise NotImplementedError("Implement get_task")

    def update_task_status(self, task_id: str, new_status: str) -> TaskModel | None:
        """Update task status."""
        # TODO: Fetch and update task
        raise NotImplementedError("Implement update_task_status")

    def delete_task(self, task_id: str) -> bool:
        """Delete task by ID."""
        # TODO: Delete task from database
        raise NotImplementedError("Implement delete_task")
