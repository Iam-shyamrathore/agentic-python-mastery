"""Topic 05: Database Service & CRUD Layer (Complete Reference Solution).

Production-grade SQLAlchemy 2.0 service with enterprise connection pooling,
transactional safety, query performance indexing, and structured database logging.

=============================================================================
📚 ARCHITECTURAL DEEP DIVE: CONNECTION POOLING IN AI AGENTS
=============================================================================

1. WHY CONNECTION POOLING MATTERS FOR AI AGENTS:
   Modern AI architectures (like LangGraph, CrewAI, AutoGen) use parallel worker
   loops and agent fan-out patterns. An agent might spawn 10 parallel subagents to
   research topics, each attempting to persist intermediate state into the database.
   Without a connection pool:
   - Every worker opens a brand-new TCP socket and TLS handshake.
   - Postgres/MySQL spawn a dedicated backend server process per connection (~5-10MB RAM).
   - A flurry of 50 concurrent agent tool calls triggers "Connection Storm" (503 Service
     Unavailable or "FATAL: remaining connection slots are reserved").

2. WHY SQLite vs. PostgreSQL CONNECTION POOLING BEHAVES DIFFERENTLY:
   - PostgreSQL / MySQL (Client-Server):
     A client-server RDBMS thrives on concurrent connections up to its hardware limit.
     Connection pools keep a fixed number of warm TCP connections (`pool_size=10`),
     absorbing bursts (`max_overflow=20`).
   - SQLite (Embedded File-Based):
     SQLite is a serverless library that locks the underlying disk file during writes.
     Default SQLite locking mode ("DELETE" journal) locks the ENTIRE file during a write,
     causing concurrent reads and writes from other threads to fail immediately with:
     `sqlite3.OperationalError: database is locked`.
     To make SQLite production-ready for multi-threaded AI services:
     a) Enable WAL (Write-Ahead Logging) mode (`PRAGMA journal_mode=WAL;`).
        WAL mode permits concurrent readers while a single writer commits changes.
     b) Set `connect_args={"check_same_thread": False}` to allow connection reuse.
     c) Bound the pool to prevent thread collision.

3. IDLE TIMEOUTS & STALE CONNECTIONS (`pool_pre_ping=True`):
   LLM API inferences (e.g. streaming a long answer from Claude or GPT-4o) frequently
   take 15 to 90 seconds. While the Python event loop awaits tokens, the database
   connection sits idle in the pool.
   Cloud load balancers, NAT gateways, and AWS RDS automatically sever idle TCP
   connections after 60-300 seconds without notifying the client.
   Without `pool_pre_ping=True`, the next agent query using that socket crashes with:
   `OperationalError: server closed the connection unexpectedly`.
   With `pool_pre_ping=True`, SQLAlchemy issues a lightweight test query (`SELECT 1`)
   before handing the socket to your code, transparently recycling dead connections.

4. POOL RECYCLING (`pool_recycle=1800`):
   Recycles connections after 30 minutes to prevent socket leaks and avoid server-side
   state decay or database credential rotation issues.
"""

from __future__ import annotations

from contextlib import contextmanager
import logging
from typing import Any, Generator, Sequence

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from models import Base, TaskModel

# ---------------------------------------------------------------------------
# Structured Database Logger
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [database] %(message)s",
)
logger = logging.getLogger("database_service")


class DatabaseService:
    """Enterprise-grade database service for AI agents and task queues.

    Handles connection pooling, session lifecycle, modern SQLAlchemy 2.0
    type-safe select statements, and transactional error boundaries.
    """

    def __init__(
        self,
        db_url: str = "sqlite:///./tasks.db",
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 1800,
        pool_pre_ping: bool = True,
        echo_sql: bool = False,
    ) -> None:
        """Initialize database engine with connection pooling and schema initialization.

        Args:
            db_url: Database connection string (SQLite, PostgreSQL, MySQL, etc.).
            pool_size: Base number of persistent connections maintained in the pool.
            max_overflow: Additional burst connections permitted during traffic spikes.
            pool_recycle: Time in seconds after which idle connections are replaced.
            pool_pre_ping: Test connection liveness before checking out from pool.
            echo_sql: If True, prints raw SQL statements to stdout (useful for debugging).
        """
        self.db_url = db_url
        engine_kwargs: dict[str, Any] = {
            "echo": echo_sql,
            "pool_pre_ping": pool_pre_ping,
            "pool_recycle": pool_recycle,
        }

        # Configure connection pool based on dialect
        if "sqlite" in db_url:
            # Enable cross-thread usage for SQLite
            engine_kwargs["connect_args"] = {"check_same_thread": False}

            if ":memory:" in db_url:
                # In-memory SQLite requires StaticPool so all threads share the memory DB
                engine_kwargs["poolclass"] = StaticPool
            else:
                # File SQLite supports QueuePool in modern SQLAlchemy
                engine_kwargs["poolclass"] = QueuePool
                engine_kwargs["pool_size"] = pool_size
                engine_kwargs["max_overflow"] = max_overflow
        else:
            # PostgreSQL / MySQL / CockroachDB enterprise pooling
            engine_kwargs["poolclass"] = QueuePool
            engine_kwargs["pool_size"] = pool_size
            engine_kwargs["max_overflow"] = max_overflow

        self.engine = create_engine(db_url, **engine_kwargs)

        # SQLite performance optimization: enable WAL mode on connect
        if "sqlite" in db_url:
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                try:
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL;")
                    cursor.execute("PRAGMA synchronous=NORMAL;")
                    cursor.close()
                except Exception as exc:
                    logger.debug("SQLite WAL pragma notice: %s", exc)

        # Thread-safe session factory
        self.SessionFactory = sessionmaker(bind=self.engine, expire_on_commit=False)

        # Ensure schema tables exist
        Base.metadata.create_all(bind=self.engine)
        logger.info(
            "Initialized DatabaseService on %s [pool_size=%s, pre_ping=%s]",
            db_url,
            pool_size if ":memory:" not in db_url else "StaticPool",
            pool_pre_ping,
        )

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Context manager providing a transactional scope around a series of operations.

        Automatically commits on success or rolls back on exception.
        Guarantees session closure to prevent connection pool leaks.
        """
        session: Session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.warning("Transaction rolled back due to error: %s", exc)
            raise
        finally:
            session.close()

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
    ) -> TaskModel:
        """Create and persist a new task with strict transactional integrity.

        Args:
            title: Descriptive name of the task.
            description: Optional details.
            priority: Urgency rating ('low', 'medium', 'high').

        Returns:
            The newly created TaskModel instance with populated ID and timestamp.
        """
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title cannot be empty or whitespace only.")

        with self.session_scope() as session:
            task = TaskModel(
                title=clean_title,
                description=description.strip(),
                priority=priority.strip().lower(),
                status="pending",
            )
            session.add(task)
            # Flush so the primary key and default values are populated before commit
            session.flush()
            logger.info("Persisted new task %s: %s [priority=%s]", task.id, task.title, task.priority)
            return task

    def get_task(self, task_id: str) -> TaskModel | None:
        """Retrieve a task by its unique identifier.

        Args:
            task_id: Unique task identifier.

        Returns:
            TaskModel if found, else None.
        """
        with self.SessionFactory() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            task = session.scalars(stmt).first()
            if task:
                logger.debug("Retrieved task %s", task_id)
            else:
                logger.debug("Task %s not found", task_id)
            return task

    def list_tasks(
        self,
        status: str | None = None,
        priority: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[TaskModel]:
        """List tasks with optional status and priority filters, plus limit/offset pagination.

        Uses modern SQLAlchemy 2.0 `select()` syntax with `scalars().all()`.

        Args:
            status: Optional filter by status ('pending', 'completed', etc.).
            priority: Optional filter by priority ('low', 'medium', 'high').
            limit: Maximum number of records to return (None for all).
            offset: Number of initial records to skip.

        Returns:
            Sequence of TaskModel instances ordered by creation date descending.
        """
        with self.SessionFactory() as session:
            stmt = select(TaskModel)
            if status:
                stmt = stmt.where(TaskModel.status == status)
            if priority:
                stmt = stmt.where(TaskModel.priority == priority)

            stmt = stmt.order_by(TaskModel.created_at.desc())

            if offset > 0:
                stmt = stmt.offset(offset)
            if limit is not None:
                stmt = stmt.limit(limit)

            tasks = session.scalars(stmt).all()
            logger.debug(
                "Listed %d tasks (status=%s, priority=%s, limit=%s, offset=%s)",
                len(tasks),
                status,
                priority,
                limit,
                offset,
            )
            return tasks

    def count_tasks(
        self,
        status: str | None = None,
        priority: str | None = None,
    ) -> int:
        """Count the total number of tasks matching the specified criteria.

        Uses database-level `func.count()` for maximal efficiency instead
        of loading full model objects into Python memory.

        Args:
            status: Optional status filter.
            priority: Optional priority filter.

        Returns:
            Integer count of matching rows.
        """
        with self.SessionFactory() as session:
            stmt = select(func.count()).select_from(TaskModel)
            if status:
                stmt = stmt.where(TaskModel.status == status)
            if priority:
                stmt = stmt.where(TaskModel.priority == priority)
            total = session.scalar(stmt) or 0
            return total

    def list_tasks_paginated(
        self,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[Sequence[TaskModel], int]:
        """Retrieve a paginated slice of tasks alongside the total matching count.

        This is the standard pagination helper for REST endpoints and UI tables.

        Args:
            status: Optional status filter.
            priority: Optional priority filter.
            limit: Number of items per page.
            offset: Number of items skipped.

        Returns:
            Tuple of (records_in_page, total_matching_count).
        """
        total = self.count_tasks(status=status, priority=priority)
        records = self.list_tasks(status=status, priority=priority, limit=limit, offset=offset)
        return records, total

    def update_task_status(self, task_id: str, new_status: str) -> TaskModel | None:
        """Update the lifecycle status of a task.

        Args:
            task_id: Unique task identifier.
            new_status: New status string ('in_progress', 'completed', etc.).

        Returns:
            Updated TaskModel if found, else None.
        """
        with self.session_scope() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            task = session.scalars(stmt).first()
            if not task:
                logger.warning("Attempted status update on non-existent task %s", task_id)
                return None
            old_status = task.status
            task.status = new_status
            session.flush()
            logger.info("Updated task %s status: %s -> %s", task_id, old_status, new_status)
            return task

    def update_task(
        self,
        task_id: str,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
    ) -> TaskModel | None:
        """Selectively update any fields on an existing task.

        Args:
            task_id: Unique task ID.
            title: Optional updated title.
            description: Optional updated description.
            status: Optional updated status.
            priority: Optional updated priority.

        Returns:
            Updated TaskModel if found, else None.
        """
        with self.session_scope() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            task = session.scalars(stmt).first()
            if not task:
                return None

            if title is not None:
                task.title = title.strip()
            if description is not None:
                task.description = description.strip()
            if status is not None:
                task.status = status.strip()
            if priority is not None:
                task.priority = priority.strip()

            session.flush()
            logger.info("Updated task %s attributes", task_id)
            return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID within a transactional boundary.

        Args:
            task_id: Unique identifier of task to delete.

        Returns:
            True if task was found and deleted, False if not found.
        """
        with self.session_scope() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            task = session.scalars(stmt).first()
            if not task:
                logger.warning("Attempted deletion of non-existent task %s", task_id)
                return False
            session.delete(task)
            logger.info("Deleted task %s (%s)", task_id, task.title)
            return True
