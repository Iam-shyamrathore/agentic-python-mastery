"""Topic 05: SQLAlchemy 2.0 Models (Complete Reference Solution).

Production-grade database models leveraging SQLAlchemy 2.0 type-safe mappings,
b-tree composite indexes for high-throughput query patterns, and domain serialization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy 2.0 models in the application.

    Subclasses inherit unified metadata and type annotations recognized by static
    analysis tools (Mypy, Pyright) and modern IDEs.
    """
    pass


class TaskModel(Base):
    """Task entity representing asynchronous work or agent goals.

    =============================================================================
    INDEXING STRATEGY FOR AI AGENTS & QUEUES:
    =============================================================================
    1. Single Column Indexes:
       - `status`: Filtered constantly to find "pending" or "in_progress" agent work.
       - `priority`: Filtered to prioritize high-urgency tasks first.
       - `created_at`: Frequently used in `ORDER BY created_at DESC` for time-series feeds.

    2. Composite B-Tree Indexes:
       - `idx_tasks_status_created_at`: Essential for the query
         `SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at DESC`.
         Without this composite index, the database engine must execute a filter
         followed by a separate in-memory sorting pass (filesort), causing latency spikes
         as table sizes grow beyond tens of thousands of rows.
       - `idx_tasks_priority_status`: Accelerates combined priority queue queries
         e.g., finding all high-priority pending items for immediate worker ingestion.
    """

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())[:8],
        doc="Unique primary key identifier (8-character UUID slice).",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Concise title or summary of the task.",
    )
    description: Mapped[str] = mapped_column(
        String(1000),
        default="",
        nullable=False,
        doc="Detailed specification or context for the task.",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        index=True,
        nullable=False,
        doc="Execution state: pending, in_progress, completed, failed.",
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default="medium",
        index=True,
        nullable=False,
        doc="Urgency rating: low, medium, high.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
        doc="UTC timestamp marking record persistence.",
    )

    __table_args__ = (
        Index("idx_tasks_status_created_at", "status", "created_at"),
        Index("idx_tasks_priority_status", "priority", "status"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance into a clean dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<TaskModel id={self.id!r} title={self.title!r} status={self.status!r} priority={self.priority!r}>"
