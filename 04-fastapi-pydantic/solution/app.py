"""Topic 04: FastAPI & Pydantic Task API (Complete Reference Solution).

Production-grade FastAPI application demonstrating:
- Pydantic v2 schemas with field validation and OpenAPI schema documentation
- ASGI lifespan event handlers (`@asynccontextmanager`)
- Structured correlation ID tracking (`X-Request-ID`) and latency profiling middleware
- Standardized, structured JSON exception handling (`RequestValidationError`, `HTTPException`)
- Query parameter filtering and pagination (`limit`, `offset`)
- Deep educational architectural commentary on ASGI event loops and Pydantic v2 core.
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
# Structured Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("fastapi_task_service")


# ---------------------------------------------------------------------------
# Pydantic Models & Domain Schemas
# ---------------------------------------------------------------------------
# Educational Note on Pydantic v2:
# Pydantic v2 replaced pure-Python parsing with `pydantic-core`, implemented in Rust.
# In AI agent systems, LLMs constantly produce JSON strings for tool execution.
# Validating high-throughput JSON payloads through Rust core yields a 5x-20x speedup
# compared to Pydantic v1, eliminating serialization bottlenecks in real-time agent loops.
# ---------------------------------------------------------------------------

class TaskPriority(str, Enum):
    """Priority level determining execution urgency in an AI workflow."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, Enum):
    """Lifecycle status of a task within the execution pipeline."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskCreate(BaseModel):
    """Request payload for creating a new task.

    Enforces strict field boundaries and forbids unexpected extra attributes
    to defend against payload tampering or malformed agent outputs.
    """
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

    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Descriptive title of the task (must not be whitespace only)",
        examples=["Index documentation embeddings into ChromaDB"],
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Optional detailed context or execution instructions for the task",
        examples=["Process markdown docs and compute 1536-dim vector embeddings."],
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Execution priority level",
        examples=["high"],
    )

    @field_validator("title")
    @classmethod
    def title_must_not_be_whitespace(cls, val: str) -> str:
        """Pydantic field validator: reject strings that are empty or whitespace-only.

        Why: In AI pipelines, prompt generators or agent steps can generate blank
        strings due to hallucination or parser flaws. Rejecting them at the API
        boundary protects the storage layer from corrupted state.
        """
        clean = val.strip()
        if not clean:
            raise ValueError("Task title cannot be empty or blank whitespace.")
        return clean


class TaskUpdate(BaseModel):
    """Request payload for updating an existing task (PATCH semantics).

    All fields are optional, allowing partial updates without overwriting untouched state.
    """
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "title": "Index documentation embeddings into ChromaDB (v2)",
                    "status": "in_progress",
                    "priority": "high",
                }
            ]
        },
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated title (must not be whitespace only)",
        examples=["Index documentation embeddings into ChromaDB (v2)"],
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Updated detailed description",
        examples=["Re-indexed with text-embedding-3-small and 512-token chunks."],
    )
    status: TaskStatus | None = Field(
        default=None,
        description="Updated lifecycle state",
        examples=["in_progress"],
    )
    priority: TaskPriority | None = Field(
        default=None,
        description="Updated priority level",
        examples=["high"],
    )

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
    """Standardized response schema representing a stored task record."""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "c1f7a902",
                    "title": "Index documentation embeddings into ChromaDB",
                    "description": "Process markdown docs and compute 1536-dim vector embeddings.",
                    "status": "pending",
                    "priority": "high",
                    "created_at": "2026-10-20T12:00:00Z",
                }
            ]
        }
    )

    id: str = Field(..., description="Unique 8-character task identifier", examples=["c1f7a902"])
    title: str = Field(..., description="Title of the task", examples=["Index documentation embeddings into ChromaDB"])
    description: str = Field(default="", description="Detailed description", examples=["Process markdown docs..."])
    status: TaskStatus = Field(..., description="Lifecycle status", examples=["pending"])
    priority: TaskPriority = Field(..., description="Execution priority", examples=["high"])
    created_at: datetime = Field(..., description="UTC creation timestamp", examples=["2026-10-20T12:00:00Z"])


# ---------------------------------------------------------------------------
# Structured Error Models
# ---------------------------------------------------------------------------
class StructuredErrorResponse(BaseModel):
    """Consistent, production-grade error response schema for API clients."""
    error: str = Field(..., description="Machine-readable error category code", examples=["VALIDATION_ERROR"])
    message: str = Field(..., description="Human-readable summary of the failure", examples=["Request validation failed."])
    details: Any = Field(default=None, description="Detailed field-level validation errors or context")
    request_id: str | None = Field(default=None, description="Correlation ID for distributed tracing")


# ---------------------------------------------------------------------------
# ASGI Lifespan Event Handler
# ---------------------------------------------------------------------------
# Architectural Note:
# In modern FastAPI (Starlette >= 0.28), `@asynccontextmanager` replaces deprecated
# `@app.on_event("startup")` and `@app.on_event("shutdown")`.
# The lifespan context manager guarantees that startup code runs before requests
# are accepted, and shutdown teardown runs when the ASGI server terminates.
# In production AI systems, this is where you warm up model caches, establish database
# connection pools, or start background telemetry workers.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: warm up resources on startup, flush on shutdown."""
    logger.info("FastAPI Task API starting up: initializing datastore & connection pools.")
    yield
    logger.info("FastAPI Task API shutting down: releasing connections and terminating workers.")


# ---------------------------------------------------------------------------
# Application Initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Task Management API",
    description=(
        "Production-grade FastAPI & Pydantic service for AI Engineers. "
        "Provides strict data validation, OpenAPI contracts, request tracing, and pagination."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# In-memory database storage for Topic 04
DATABASE: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Custom Middleware: Request Timing & Distributed Tracing Correlation ID
# ---------------------------------------------------------------------------
# Architectural Note:
# Microservices and multi-agent systems require distributed tracing.
# By generating or propagating an `X-Request-ID` correlation header, every log line
# across FastAPI, LLM API calls, and SQL queries can be tied to a single user interaction.
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_correlation_and_timing_middleware(request: Request, call_next):
    """Attach correlation ID (X-Request-ID) and record request duration in headers."""
    # Propagate client-supplied correlation ID or generate a new UUID4
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.perf_counter()
    try:
        response: Response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000

        # Inject tracing and performance headers into response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"

        logger.info(
            "%s %s -> HTTP %d (%.2f ms) [request_id=%s]",
            request.method,
            request.url.path,
            response.status_code,
            process_time_ms,
            request_id,
        )
        return response
    except Exception as exc:
        process_time_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "Unhandled failure processing %s %s after %.2f ms [request_id=%s]: %s",
            request.method,
            request.url.path,
            process_time_ms,
            request_id,
            exc,
        )
        raise


# ---------------------------------------------------------------------------
# Custom Exception Handlers with Structured JSON Schemas
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Transform Pydantic validation errors into a structured JSON error response.

    Educational Note on Pydantic v2 Serialization:
    In Pydantic v2, `exc.errors()` can include raw Python Exception instances inside
    the `ctx` dictionary (e.g. `ctx: {'error': ValueError(...)}`). Passing `exc.errors()`
    directly to `json.dumps()` raises `TypeError: Object of type ValueError is not JSON
    serializable`. Using FastAPI's `jsonable_encoder` safely coerces complex Python types
    into standard JSON-safe primitives.
    """
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    safe_errors = jsonable_encoder(exc.errors())
    logger.warning(
        "Validation error on %s %s [request_id=%s]: %s",
        request.method,
        request.url.path,
        request_id,
        safe_errors,
    )
    headers = {"X-Request-ID": request_id} if request_id else {}
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": "VALIDATION_ERROR",
            "message": "The request payload or query parameters failed schema validation.",
            "details": safe_errors,
            "request_id": request_id,
        },
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Format HTTP exceptions into a uniform error contract."""
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    logger.warning(
        "HTTP %d error on %s %s [request_id=%s]: %s",
        exc.status_code,
        request.method,
        request.url.path,
        request_id,
        exc.detail,
    )
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
# REST Endpoints
# ---------------------------------------------------------------------------
# Architectural Note on `async def` vs `def` in FastAPI:
# - `async def`: Executed directly on the main event loop thread. Ideal for I/O-bound
#   calls using `await` (e.g. `await httpx_client.get()`, `await aiosqlite.execute()`).
#   WARNING: If you run CPU-heavy code or blocking sync calls (e.g., `requests.get()`
#   or long regex parsing) in `async def`, you will block the entire event loop!
# - `def`: FastAPI automatically dispatches regular synchronous `def` endpoints to a
#   threadpool (`anyio.to_thread.run_sync`), preventing event loop starvation.
# ---------------------------------------------------------------------------

@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    responses={
        201: {"description": "Task created successfully", "model": TaskResponse},
        422: {"description": "Payload validation failed", "model": StructuredErrorResponse},
    },
)
async def create_task(payload: TaskCreate):
    """Create a new task with automatic ID assignment and UTC timestamping."""
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
    logger.info("Created task %s with priority=%s", task_id, payload.priority.value)
    return task_record


@app.get(
    "/tasks",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List all tasks with filtering and pagination",
    responses={
        200: {
            "description": "Paginated list of task records",
            "headers": {
                "X-Total-Count": {
                    "description": "Total number of records matching criteria before pagination",
                    "schema": {"type": "integer"},
                }
            },
        },
        422: {"description": "Invalid query parameters", "model": StructuredErrorResponse},
    },
)
async def list_tasks(
    response: Response,
    status_filter: TaskStatus | None = Query(
        default=None,
        alias="status",
        description="Filter tasks by lifecycle state",
    ),
    priority_filter: TaskPriority | None = Query(
        default=None,
        alias="priority",
        description="Filter tasks by execution urgency",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of tasks to return (pagination limit: 1-100)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of matching tasks to skip (pagination offset >= 0)",
    ),
):
    """Retrieve tasks with optional status and priority filtering, plus offset/limit pagination."""
    results = list(DATABASE.values())
    if status_filter:
        results = [t for t in results if t["status"] == status_filter]
    if priority_filter:
        results = [t for t in results if t["priority"] == priority_filter]

    # Deterministic sort: newest first
    sorted_results = sorted(results, key=lambda x: x["created_at"], reverse=True)

    # Expose total count in response headers for client pagination UIs
    response.headers["X-Total-Count"] = str(len(sorted_results))

    # Apply pagination slice
    paginated_results = sorted_results[offset : offset + limit]
    return paginated_results


@app.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task by ID",
    responses={
        200: {"description": "Task record found", "model": TaskResponse},
        404: {"description": "Task ID not found", "model": StructuredErrorResponse},
    },
)
async def get_task(task_id: str):
    """Fetch an existing task by its 8-character ID or return 404 Not Found."""
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
    summary="Selectively update task fields",
    responses={
        200: {"description": "Task updated successfully", "model": TaskResponse},
        404: {"description": "Task ID not found", "model": StructuredErrorResponse},
        422: {"description": "Update validation failed", "model": StructuredErrorResponse},
    },
)
async def update_task(task_id: str, payload: TaskUpdate):
    """Selectively update fields on an existing task without overwriting untouched attributes."""
    if task_id not in DATABASE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' does not exist.",
        )
    record = DATABASE[task_id]

    # Exclude unset fields so omitted attributes are NOT wiped
    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        record[field_name] = value

    logger.info("Updated task %s: fields modified = %s", task_id, list(update_data.keys()))
    return record


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task by ID",
    responses={
        204: {"description": "Task successfully deleted; no content returned"},
        404: {"description": "Task ID not found", "model": StructuredErrorResponse},
    },
)
async def delete_task(task_id: str):
    """Delete a task by ID or return 404 if not found."""
    if task_id not in DATABASE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' does not exist.",
        )
    del DATABASE[task_id]
    logger.info("Deleted task %s", task_id)
    return None
