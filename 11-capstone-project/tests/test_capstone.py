"""Tests for Topic 11: The Unified Capstone Project."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from main import (
    ResearchRecord,
    SessionFactory,
    app,
    knowledge_collection,
    rag_retrieval_node,
    research_semaphore,
)


client = TestClient(app)


def test_health_check_endpoint():
    """Verify health endpoint diagnostics, DB connection, and active concurrency slots."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["vector_docs_indexed"] >= 5
    assert "active_concurrency_slots" in data
    assert data["max_concurrency_limit"] >= 1


def test_research_api_execution_and_persistence():
    """Verify end-to-end execution of agent research workflow with DB persistence."""
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


def test_request_tracing_middleware():
    """Verify structured request tracing middleware injects X-Request-ID and timing."""
    custom_trace_id = "test-trace-id-999"
    response = client.get("/health", headers={"X-Request-ID": custom_trace_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_trace_id
    assert "X-Response-Time-Ms" in response.headers

    # Auto-generated UUID when no header supplied
    auto_response = client.get("/health")
    assert auto_response.status_code == 200
    assert auto_response.headers.get("X-Request-ID") is not None
    assert len(auto_response.headers["X-Request-ID"]) > 0


def test_streaming_sse_endpoint():
    """Verify Server-Sent Events (SSE) stream emits real-time workflow events."""
    payload = {"topic": "Streaming Agent Workflows with SSE"}
    with client.stream("POST", "/research/stream", json=payload) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        lines = [line for line in response.iter_lines() if line]
        assert len(lines) >= 3

        # Check for start, node update, and completed events
        events_found = []
        for line in lines:
            if line.startswith("event:"):
                events_found.append(line.replace("event:", "").strip())

        assert "started" in events_found
        assert "node_update" in events_found
        assert "completed" in events_found


def test_concurrency_semaphore_limit():
    """Verify research semaphore tracks available execution slots."""
    assert research_semaphore._value >= 0


def test_research_not_found_404():
    """Verify 404 response on querying non-existent research record."""
    response = client.get("/research/non_existent_record_id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_validation_error_on_invalid_topic():
    """Verify 422 Unprocessable Entity when topic contract is violated."""
    # Topic too short (< 2 characters)
    response = client.post("/research", json={"topic": "x"})
    assert response.status_code == 422

    # Missing topic field
    response_missing = client.post("/research", json={})
    assert response_missing.status_code == 422


def test_rag_retrieval_fallback_on_unmatched_query():
    """Verify RAG retrieval handles novel or empty queries gracefully without crashing."""
    state = {
        "topic": "Quantum Computing Superconductors 987654321",
        "context_chunks": [],
        "notes": [],
        "critique": "",
        "revisions": 0,
        "final_report": "",
    }
    result = rag_retrieval_node(state)
    assert "context_chunks" in result
    assert len(result["context_chunks"]) >= 1
