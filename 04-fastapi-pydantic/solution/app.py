"""Topic 04: FastAPI & Pydantic Task API (Complete Reference Solution).

Production-grade FastAPI application demonstrating Pydantic v2 schemas,
field validators, query parameter filtering, proper HTTP status codes,
and exception handling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="Title of the task")
    description: str = Field(default="", max_length=500, description="Optional detailed description")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority level")

    @field_validator("title")
    @classmethod
    def title_must_not_be_whitespace(cls, val: str) -> str:
        clean = val.strip()
        if not clean:
            raise ValueError("Task title cannot be empty or blank whitespace.")
        return clean


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, val: str | None) -> str | None:
        if val is not None:
            clean = val.strip()
            if not clean:
                raise ValueError("Updated title cannot be whitespace only.")
            return clean
        return val


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime


app = FastAPI(
    title="Task Management API",
    description="Production-grade FastAPI & Pydantic service for AI Engineers",
    version="1.0.0",
)

# In-memory database dictionary for Topic 04
DATABASE: dict[str, dict[str, Any]] = {}


@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
async def create_task(payload: TaskCreate):
    """Create a new task with automatic ID assignment and timestamping."""
    task_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc)
    task_record = {
        "id": task_id,
        "title": payload.title,
        "description": payload.description,
        "status": TaskStatus.PENDING,
        "priority": payload.priority,
        "created_at": now,
    }
    DATABASE[task_id] = task_record
    return task_record


@app.get(
    "/tasks",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List all tasks",
)
async def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status", description="Filter by task status"),
    priority_filter: TaskPriority | None = Query(default=None, alias="priority", description="Filter by task priority"),
):
    """Retrieve all tasks with optional status and priority filtering."""
    results = list(DATABASE.values())
    if status_filter:
        results = [t for t in results if t["status"] == status_filter]
    if priority_filter:
        results = [t for t in results if t["priority"] == priority_filter]
    return sorted(results, key=lambda x: x["created_at"], reverse=True)


@app.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task by ID",
)
async def get_task(task_id: str):
    """Fetch an existing task or return 404 Not Found."""
    if task_id not in DATABASE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' does not exist.",
        )
    return DATABASE[task_id]


@app.patch(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update task",
)
async def update_task(task_id: str, payload: TaskUpdate):
    """Selectively update fields on a task."""
    if task_id not in DATABASE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' does not exist.",
        )
    record = DATABASE[task_id]
    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        record[field_name] = value
    return record


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
)
async def delete_task(task_id: str):
    """Delete a task by ID or return 404."""
    if task_id not in DATABASE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' does not exist.",
        )
    del DATABASE[task_id]
    return None
