"""Topic 05: Database Service & CRUD Layer (Complete Reference Solution).

Production-grade SQLAlchemy 2.0 service with connection management,
transactional safety, and type safety.
"""

from __future__ import annotations

from typing import Sequence
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from models import Base, TaskModel


class DatabaseService:
    def __init__(self, db_url: str = "sqlite:///./tasks.db") -> None:
        self.engine = create_engine(db_url, echo=False)
        self.SessionFactory = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def add_task(self, title: str, description: str = "", priority: str = "medium") -> TaskModel:
        """Create and persist a new task with transactional safety."""
        with self.SessionFactory() as session:
            try:
                task = TaskModel(title=title.strip(), description=description.strip(), priority=priority)
                session.add(task)
                session.commit()
                session.refresh(task)
                return task
            except Exception:
                session.rollback()
                raise

    def list_tasks(self, status: str | None = None) -> Sequence[TaskModel]:
        """List tasks with optional status filter."""
        with self.SessionFactory() as session:
            stmt = select(TaskModel)
            if status:
                stmt = stmt.where(TaskModel.status == status)
            stmt = stmt.order_by(TaskModel.created_at.desc())
            return session.scalars(stmt).all()

    def get_task(self, task_id: str) -> TaskModel | None:
        """Get task by ID."""
        with self.SessionFactory() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            return session.scalars(stmt).first()

    def update_task_status(self, task_id: str, new_status: str) -> TaskModel | None:
        """Update task status."""
        with self.SessionFactory() as session:
            try:
                stmt = select(TaskModel).where(TaskModel.id == task_id)
                task = session.scalars(stmt).first()
                if not task:
                    return None
                task.status = new_status
                session.commit()
                session.refresh(task)
                return task
            except Exception:
                session.rollback()
                raise

    def delete_task(self, task_id: str) -> bool:
        """Delete task by ID."""
        with self.SessionFactory() as session:
            try:
                stmt = select(TaskModel).where(TaskModel.id == task_id)
                task = session.scalars(stmt).first()
                if not task:
                    return False
                session.delete(task)
                session.commit()
                return True
            except Exception:
                session.rollback()
                raise
