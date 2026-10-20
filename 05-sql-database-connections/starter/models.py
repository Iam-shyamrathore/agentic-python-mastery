"""Topic 05: SQLAlchemy 2.0 Models (Starter Template).

Master modern SQLAlchemy 2.0 declarative models, type-safe mapped columns,
and indexing strategies for agentic applications.

=============================================================================
📚 MODERN SQLALCHEMY 2.0 MENTAL MODEL:
=============================================================================
1. `DeclarativeBase`:
   Replaces the legacy `declarative_base()` factory function from SQLAlchemy 1.x.
   Inheriting from `DeclarativeBase` gives your models standard metadata and typing hooks.

2. `Mapped[T]` and `mapped_column()`:
   In SQLAlchemy 1.x, models used `id = Column(String, primary_key=True)`.
   Type checkers saw `id` as `Column`, causing mypy errors when treating it like `str`.
   SQLAlchemy 2.0 uses Python type annotations: `id: Mapped[str] = mapped_column(...)`.
   Now, `task.id` is statically recognized as a Python `str`.

3. INDEXING PHILOSOPHY:
   Databases are slow when searching unindexed columns (O(N) table scan).
   Add `index=True` for single-column lookups (e.g. `status="pending"`).
   Define composite indexes in `__table_args__` for queries filtering on one column
   and sorting by another (e.g., `WHERE status = 'pending' ORDER BY created_at DESC`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy 2.0."""
    pass


class TaskModel(Base):
    """Task entity stored in the database.

    Follow the steps below to define the table schema and indexes.
    """

    __tablename__ = "tasks"

    # -----------------------------------------------------------------------
    # STEP 1: Define Columns using Mapped[T] and mapped_column()
    # -----------------------------------------------------------------------
    # id: primary key, String(36), default 8-char uuid slice
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())[:8],
    )

    # title: non-nullable String(255)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # description: non-nullable String(1000), default empty string
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)

    # status: indexed String(50), default "pending", non-nullable
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True, nullable=False)

    # priority: indexed String(50), default "medium", non-nullable
    priority: Mapped[str] = mapped_column(String(50), default="medium", index=True, nullable=False)

    # created_at: indexed DateTime with timezone, default UTC now, non-nullable
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    # -----------------------------------------------------------------------
    # STEP 2: Define Composite Indexes for Multi-Attribute Queries
    # -----------------------------------------------------------------------
    # HINT: In AI queues, queries frequently filter by status and sort by created_at.
    # Define a tuple of Index objects in __table_args__:
    __table_args__ = (
        Index("idx_tasks_status_created_at", "status", "created_at"),
        Index("idx_tasks_priority_status", "priority", "status"),
    )

    # -----------------------------------------------------------------------
    # STEP 3: Domain Helpers
    # -----------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Convert task model to dictionary for API responses."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<TaskModel id={self.id!r} title={self.title!r} status={self.status!r}>"
