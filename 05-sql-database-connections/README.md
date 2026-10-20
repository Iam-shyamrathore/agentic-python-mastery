# 🗄️ Topic 05: SQL & Database Connections for AI Engineers

> **Master relational database modeling, connection pooling, transactions, and modern SQLAlchemy 2.0 ORM for AI applications.**

---

## 🎯 Why Databases are Critical for AI Engineers

Real-world AI systems rely on transactional databases for:
1. **Agent State & Memory Checkpointing**: LangGraph and CrewAI store conversation state and graph checkpoints in SQLite or PostgreSQL.
2. **Audit Logging & Tracing**: Storing exact user prompts, model parameters, retrieved context, and raw tool outputs for compliance and evals.
3. **User & Usage Quotas**: Tracking API token counts, rate limits, and billing tiers reliably.

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. Modern SQLAlchemy 2.0 Syntax (Avoid Legacy 1.4!)

SQLAlchemy 2.0 completely rewrote the ORM to be fully type-hinted and clean.

```python
from datetime import datetime, timezone
import uuid
from sqlalchemy import String, DateTime, Enum as SQLEnum, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

class Base(DeclarativeBase):
    pass

class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="")
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# Engine & Session Setup
DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionFactory = sessionmaker(bind=engine)

# Creating tables
Base.metadata.create_all(bind=engine)

# Querying with 2.0 Select syntax
with SessionFactory() as session:
    stmt = select(TaskModel).where(TaskModel.status == "pending")
    tasks = session.scalars(stmt).all()
```

---

### 2. Transaction Management & Rollback Safety

Never leave transactions hanging. Always use context managers to guarantee rollback on exception.

```python
def add_task_safely(title: str, description: str = "") -> TaskModel:
    with SessionFactory() as session:
        try:
            new_task = TaskModel(title=title, description=description)
            session.add(new_task)
            session.commit()
            session.refresh(new_task)
            return new_task
        except Exception:
            session.rollback()
            raise
```

---

## 🛠️ The Hands-on Project: Persistent Task Tracker

In this module, you will build a complete database-backed task tracker:
- SQLAlchemy 2.0 typed models (`TaskModel`)
- Engine configuration with SQLite / PostgreSQL compatibility
- Safe transactional CRUD service layer (`add_task`, `get_task`, `list_tasks`, `update_task`, `delete_task`)
- Automated verification tests

### Running the Tests
```bash
pytest 05-sql-database-connections/tests/test_database.py -v
```
