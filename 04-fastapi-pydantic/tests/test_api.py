"""Tests for Topic 04: FastAPI & Pydantic Task API."""

import sys
from pathlib import Path
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
    assert data["priority"] == "high"
    assert data["status"] == "pending"
    assert "id" in data


def test_create_task_validation_failure():
    # Empty title should be rejected by field_validator
    payload = {"title": "   ", "priority": "medium"}
    response = client.post("/tasks", json=payload)
    assert response.status_code == 422


def test_list_and_filter_tasks():
    client.post("/tasks", json={"title": "Task 1", "priority": "low"})
    client.post("/tasks", json={"title": "Task 2", "priority": "high"})

    # All
    res = client.get("/tasks")
    assert res.status_code == 200
    assert len(res.json()) == 2

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
