# ⚡ Topic 04: FastAPI & Pydantic for AI Engineers

> **Master high-performance Python web APIs, Pydantic v2 data validation, request/response contracts, and dependency injection.**

---

## 🎯 Why FastAPI & Pydantic are the Bedrock of Modern AI

Nearly every modern AI framework is built on top of Pydantic and served through FastAPI:
- **Pydantic v2**: Written in Rust, it provides microsecond data validation. Both OpenAI's structured outputs (`client.beta.chat.completions.parse()`) and Instructor rely directly on Pydantic `BaseModel`.
- **FastAPI**: Provides native async performance, automatic interactive OpenAPI docs (`/docs`), strict type contracts, and dependency injection.

When deploying an AI agent, RAG service, or embedding endpoint, FastAPI is the universal tool of choice.

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. Pydantic v2 Data Modeling

```python
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime, timezone
import uuid

class PriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="Title of the task")
    description: str = Field(default="", max_length=500)
    priority: PriorityEnum = PriorityEnum.MEDIUM

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be whitespace only.")
        return v.strip()

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    priority: PriorityEnum
    is_completed: bool = False
    created_at: datetime
```

---

### 2. FastAPI Route Handlers & Status Codes

```python
from fastapi import FastAPI, HTTPException, status, Query

app = FastAPI(title="AI Task API", version="1.0.0")

# In-memory storage mock
DB: dict[str, dict] = {}

@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate):
    task_id = str(uuid.uuid4())[:8]
    task_data = {
        "id": task_id,
        **payload.model_dump(),
        "is_completed": False,
        "created_at": datetime.now(timezone.utc),
    }
    DB[task_id] = task_data
    return task_data

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    if task_id not in DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' not found."
        )
    return DB[task_id]
```

---

## 🛠️ The Hands-on Project: Task Management API

In this module, you will build a production-ready REST API in `starter/app.py`:
- Pydantic v2 schemas for creation, update, and response
- Clean CRUD endpoints (`POST`, `GET`, `PATCH`, `DELETE`)
- Query parameter filtering and pagination
- Custom error handling with proper HTTP status codes
- Interactive Swagger UI documentation at `http://127.0.0.1:8000/docs`

### Running the Tests
```bash
pytest 04-fastapi-pydantic/tests/test_api.py -v
```
