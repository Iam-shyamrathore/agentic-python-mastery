"""Tests for Topic 11: The Unified Capstone Project."""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from main import app, knowledge_collection, SessionFactory, ResearchRecord


client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["vector_docs_indexed"] >= 5


def test_research_api_execution_and_persistence():
    payload = {"topic": "Asynchronous Event Loops in Agent Systems"}
    response = client.post("/research", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["topic"] == payload["topic"]
    assert data["status"] == "completed"
    assert "id" in data
    assert len(data["final_report"]) > 0

    record_id = data["id"]

    # Verify retrieval by ID
    get_res = client.get(f"/research/{record_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == record_id

    # Verify listing
    list_res = client.get("/research")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
