"""Topic 04: FastAPI & Pydantic Task API (Starter Template).

Complete each TODO section alongside your AI Assistant.
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
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime


app = FastAPI(title="Task Management API", version="1.0.0")

# In-memory dictionary database for Topic 04
DATABASE: dict[str, dict[str, Any]] = {}


@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate):
    """Create a new task."""
    # TODO: Generate ID and created_at, store in DATABASE, and return task
    raise NotImplementedError("Implement create_task")


@app.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    priority_filter: TaskPriority | None = Query(default=None, alias="priority"),
):
    """List all tasks with optional status and priority filtering."""
    # TODO: Filter items in DATABASE and return list
    raise NotImplementedError("Implement list_tasks")


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Retrieve a single task by ID."""
    # TODO: Retrieve from DATABASE or raise HTTPException 404
    raise NotImplementedError("Implement get_task")


@app.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, payload: TaskUpdate):
    """Update fields on an existing task."""
    # TODO: Update task fields or raise HTTPException 404
    raise NotImplementedError("Implement update_task")


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str):
    """Delete a task."""
    # TODO: Remove from DATABASE or raise HTTPException 404
    raise NotImplementedError("Implement delete_task")
