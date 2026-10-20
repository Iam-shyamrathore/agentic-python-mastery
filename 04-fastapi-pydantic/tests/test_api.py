"""Tests for Topic 04: FastAPI & Pydantic Task API.

Validates core CRUD operations, Pydantic v2 schemas, correlation ID tracking,
request timing headers, structured error responses, and pagination.
"""

from __future__ import annotations

import sys
from pathlib import Path
import uuid
import pytest
from fastapi.testclient import TestClient

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from app import DATABASE, app


@pytest.fixture(autouse=True)
def clear_db():
    DATABASE.clear()
    yield
    DATABASE.clear()


client = TestClient(app)


def test_create_task_success():
    payload = {
        "title": "Build RAG Pipeline",
        "description": "Index documents into ChromaDB",
        "priority": "high",
    }
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Build RAG Pipeline"
    assert data["description"] == "Index documents into ChromaDB"
    assert data["priority"] == "high"
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


def test_create_task_validation_failure():
    # Empty/whitespace title should be rejected by field_validator
    payload = {"title": "   ", "priority": "medium"}
    response = client.post("/tasks", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "VALIDATION_ERROR"
    assert "details" in data
    assert "request_id" in data


def test_list_and_filter_tasks():
    client.post("/tasks", json={"title": "Task 1", "priority": "low"})
    client.post("/tasks", json={"title": "Task 2", "priority": "high"})

    # All
    res = client.get("/tasks")
    assert res.status_code == 200
    assert len(res.json()) == 2
    assert res.headers.get("X-Total-Count") == "2"

    # Filter high
    res_high = client.get("/tasks?priority=high")
    assert res_high.status_code == 200
    assert len(res_high.json()) == 1
    assert res_high.json()[0]["title"] == "Task 2"


def test_get_and_update_task():
    create_res = client.post("/tasks", json={"title": "Task to update", "priority": "medium"})
    task_id = create_res.json()["id"]

    # Get
    get_res = client.get(f"/tasks/{task_id}")
    assert get_res.status_code == 200

    # Patch
    patch_res = client.patch(f"/tasks/{task_id}", json={"status": "completed", "title": "Updated Title"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "completed"
    assert patch_res.json()["title"] == "Updated Title"


def test_delete_task():
    create_res = client.post("/tasks", json={"title": "Task to delete"})
    task_id = create_res.json()["id"]

    del_res = client.delete(f"/tasks/{task_id}")
    assert del_res.status_code == 204

    # Verify 404
    get_res = client.get(f"/tasks/{task_id}")
    assert get_res.status_code == 404


def test_correlation_id_headers_generated_and_propagated():
    """Verify that correlation ID is auto-generated or propagated from client headers."""
    # 1. Auto-generated correlation ID
    res_auto = client.get("/tasks")
    assert "X-Request-ID" in res_auto.headers
    assert "X-Process-Time-Ms" in res_auto.headers
    assert len(res_auto.headers["X-Request-ID"]) > 0

    # 2. Client-supplied correlation ID propagated
    custom_id = "trace-" + str(uuid.uuid4())
    res_custom = client.get("/tasks", headers={"X-Request-ID": custom_id})
    assert res_custom.headers["X-Request-ID"] == custom_id


def test_pagination_limit_and_offset():
    """Verify limit and offset pagination controls with X-Total-Count header."""
    for i in range(5):
        client.post("/tasks", json={"title": f"Task {i + 1}", "priority": "medium"})

    # Page 1: limit 2, offset 0
    p1 = client.get("/tasks?limit=2&offset=0")
    assert p1.status_code == 200
    assert len(p1.json()) == 2
    assert p1.headers.get("X-Total-Count") == "5"

    # Page 2: limit 2, offset 2
    p2 = client.get("/tasks?limit=2&offset=2")
    assert p2.status_code == 200
    assert len(p2.json()) == 2

    # Verify items between pages are disjoint
    p1_ids = {t["id"] for t in p1.json()}
    p2_ids = {t["id"] for t in p2.json()}
    assert p1_ids.isdisjoint(p2_ids)

    # Offset beyond dataset
    p_empty = client.get("/tasks?limit=2&offset=10")
    assert p_empty.status_code == 200
    assert p_empty.json() == []


def test_invalid_query_params():
    """Verify query parameter boundary validations (min/max limits and enums)."""
    # Negative limit
    res_neg_limit = client.get("/tasks?limit=-1")
    assert res_neg_limit.status_code == 422
    assert res_neg_limit.json()["error"] == "VALIDATION_ERROR"

    # Zero limit (ge=1 required)
    res_zero_limit = client.get("/tasks?limit=0")
    assert res_zero_limit.status_code == 422

    # Limit exceeding max 100
    res_high_limit = client.get("/tasks?limit=150")
    assert res_high_limit.status_code == 422

    # Negative offset
    res_neg_offset = client.get("/tasks?offset=-5")
    assert res_neg_offset.status_code == 422

    # Invalid enum value
    res_bad_enum = client.get("/tasks?priority=urgent_critical")
    assert res_bad_enum.status_code == 422


def test_not_found_structured_error():
    """Verify 404 responses follow the standardized error JSON contract."""
    res = client.get("/tasks/nonexistent-uuid")
    assert res.status_code == 404
    data = res.json()
    assert data["error"] == "HTTP_ERROR"
    assert "nonexistent-uuid" in data["message"]
    assert "request_id" in data


def test_partial_update_preserves_unmodified_fields():
    """Verify PATCH updates only explicitly provided fields."""
    create_res = client.post(
        "/tasks",
        json={"title": "Original Title", "description": "Original Desc", "priority": "low"},
    )
    task_id = create_res.json()["id"]

    # Update only priority
    patch_res = client.patch(f"/tasks/{task_id}", json={"priority": "high"})
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["priority"] == "high"
    assert data["title"] == "Original Title"
    assert data["description"] == "Original Desc"
    assert data["status"] == "pending"
