"""Topic 04: FastAPI & Pydantic Task API (Starter Template).

Master production-grade FastAPI web services and Pydantic v2 data contracts.
Follow the guided steps (STEP 1 through STEP 5) to build a robust, observable API.

=============================================================================
📚 THE PYDANTIC v2 VALIDATION LIFECYCLE (MENTAL MODEL FOR AI ENGINEERS)
=============================================================================
When an HTTP request hits a FastAPI endpoint expecting a Pydantic model:
1. RAW INPUT: ASGI receives the raw HTTP byte stream and parses it into a Python dict.
2. CORE RUST PARSING: Pydantic v2 hands the dict to `pydantic-core` (written in Rust),
   which performs zero-copy validation against compiled bytecode validator routines.
3. PRE-VALIDATORS (`mode='before'`): Optional functions that mutate or coerce raw input
   before type checking occurs.
4. TYPE COERCION & CONSTRAINT CHECKS: Pydantic strictly validates types (str, int, enum)
   and applies `Field(min_length=..., max_length=..., ge=...)` constraints.
5. POST-VALIDATORS (`mode='after'` / default `@field_validator`): Domain-specific rules
   (e.g., ensuring a string isn't pure whitespace).
6. MODEL-LEVEL VALIDATORS (`@model_validator`): Validates cross-field dependencies
   (e.g., end_date must be after start_date).
7. ERROR COLLECTION: If any step fails, Pydantic halts instantiation and raises a
   `RequestValidationError` containing a list of all violated constraints.

=============================================================================
🛡️ PRODUCTION EDGE-CASE CHECKLIST TO CONSIDER
=============================================================================
[ ] Whitespace strings: A string with 5 spaces ("     ") satisfies `min_length=1`!
    Always strip and validate in a `@field_validator`.
[ ] Missing vs None in PATCH: When updating, distinguish between an omitted field
    and a field explicitly set to None using `payload.model_dump(exclude_unset=True)`.
[ ] Non-existent IDs: Querying, updating, or deleting a missing task ID must raise
    HTTP 404 with a structured error response, never return null or crash with KeyError.
[ ] Distributed Tracing: Every request must carry an `X-Request-ID` correlation header
    so logs across microservices and LLM calls can be correlated.
[ ] JSON Serialization in Error Handlers: In Pydantic v2, `exc.errors()` can contain
    raw `ValueError` objects in the `ctx` dict. Always use `fastapi.encoders.jsonable_encoder`
    to avoid `TypeError: Object of type ValueError is not JSON serializable`.
[ ] Non-blocking Event Loop: Never call blocking I/O (like `time.sleep` or synchronous
    database drivers) inside `async def` endpoints, as it freezes all concurrent requests.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
import logging
import time
from typing import Any
import uuid

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("task_api")


# ---------------------------------------------------------------------------
# STEP 1: Pydantic Domain Schemas & Enums
# ---------------------------------------------------------------------------

class TaskPriority(str, Enum):
    """Execution priority levels for tasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, Enum):
    """Lifecycle states of a task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskCreate(BaseModel):
    """Schema for creating a task."""
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "title": "Index documentation embeddings into ChromaDB",
                    "description": "Process markdown docs and compute 1536-dim vector embeddings.",
                    "priority": "high",
                }
            ]
        },
    )

    # HINT: Define `title` with min_length=1, max_length=100, and a realistic description.
    title: str = Field(..., min_length=1, max_length=100, description="Title of the task")
    description: str = Field(default="", max_length=500, description="Optional description")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")

    @field_validator("title")
    @classmethod
    def title_must_not_be_whitespace(cls, val: str) -> str:
        """HINT: Check that val.strip() is not empty. If empty, raise ValueError."""
        clean = val.strip()
        if not clean:
            raise ValueError("Task title cannot be empty or blank whitespace.")
        return clean


class TaskUpdate(BaseModel):
    """Schema for updating an existing task (PATCH)."""
    model_config = ConfigDict(extra="forbid")

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
    """Schema for serialized task output."""
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime


class StructuredErrorResponse(BaseModel):
    """Standardized error contract."""
    error: str
    message: str
    details: Any = None
    request_id: str | None = None


# ---------------------------------------------------------------------------
# STEP 2: Application Lifespan
# ---------------------------------------------------------------------------
# Modern FastAPI uses `@asynccontextmanager` for clean setup and teardown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, flush/close on shutdown."""
    # TODO: Log application startup, initialize DB/caches if needed
    logger.info("Application starting up...")
    yield
    # TODO: Log application shutdown, close connections
    logger.info("Application shutting down...")


app = FastAPI(
    title="Task Management API",
    description="Production-grade FastAPI & Pydantic service for AI Engineers",
    version="1.0.0",
    lifespan=lifespan,
)

# In-memory dictionary database for Topic 04
DATABASE: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# STEP 3: Correlation ID & Request Timing Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_correlation_and_timing_middleware(request: Request, call_next):
    """HINT:
    1. Extract 'X-Request-ID' from request headers or generate `str(uuid.uuid4())`.
    2. Store it on `request.state.request_id = request_id`.
    3. Measure start time with `time.perf_counter()`.
    4. Call `response = await call_next(request)`.
    5. Calculate elapsed ms and inject 'X-Request-ID' and 'X-Process-Time-Ms' into response.headers.
    6. Return response.
    """
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()

    try:
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        return response
    except Exception:
        raise


# ---------------------------------------------------------------------------
# STEP 4: Structured Error Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """HINT: Use `jsonable_encoder(exc.errors())` to serialize Pydantic errors safely.
    Return status_code=422 with StructuredErrorResponse format.
    """
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    safe_details = jsonable_encoder(exc.errors())
    headers = {"X-Request-ID": request_id} if request_id else {}
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": "VALIDATION_ERROR",
            "message": "The request payload failed validation.",
            "details": safe_details,
            "request_id": request_id,
        },
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    headers = {"X-Request-ID": request_id} if request_id else {}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "status_code": exc.status_code,
            "request_id": request_id,
        },
        headers=headers,
    )


# ---------------------------------------------------------------------------
# STEP 5: Route Handlers
# ---------------------------------------------------------------------------

@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate):
    """Create a new task.

    HINT:
    1. Generate an 8-character ID: `str(uuid.uuid4())[:8]`.
    2. Get current UTC timestamp: `datetime.now(timezone.utc)`.
    3. Construct task dictionary with PENDING status.
    4. Store in `DATABASE[task_id]` and return.
    """
    # TODO: Implement create_task
    raise NotImplementedError("Implement create_task")


@app.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    response: Response,
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    priority_filter: TaskPriority | None = Query(default=None, alias="priority"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all tasks with optional status/priority filtering and pagination.

    HINT:
    1. Filter `DATABASE.values()` matching `status_filter` and `priority_filter`.
    2. Sort results by created_at descending.
    3. Set `response.headers["X-Total-Count"] = str(len(sorted_results))`.
    4. Return slice `sorted_results[offset : offset + limit]`.
    """
    # TODO: Implement list_tasks
    raise NotImplementedError("Implement list_tasks")


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Retrieve a single task by ID or raise HTTPException(404)."""
    # TODO: Implement get_task
    raise NotImplementedError("Implement get_task")


@app.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, payload: TaskUpdate):
    """Update fields on an existing task.

    HINT:
    1. Check if `task_id in DATABASE`. If not, raise HTTPException(404).
    2. Call `payload.model_dump(exclude_unset=True)` so unset fields are ignored.
    3. Update the matching keys in the record.
    4. Return the updated record.
    """
    # TODO: Implement update_task
    raise NotImplementedError("Implement update_task")


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str):
    """Delete a task or raise HTTPException(404)."""
    # TODO: Implement delete_task
    raise NotImplementedError("Implement delete_task")
