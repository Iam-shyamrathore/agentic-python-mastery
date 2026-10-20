"""Tests for Topic 09: RAG, Embeddings & Vector DBs."""

import sys
from pathlib import Path
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from rag_app import RAGEngine, TextChunk, chunk_text


def test_chunking_with_overlap():
    sample_text = "Python is an incredible language. It is widely used in artificial intelligence and machine learning."
    chunks = chunk_text(sample_text, chunk_size=40, chunk_overlap=10)
    assert len(chunks) > 1
    # Verify non-empty
    for c in chunks:
        assert len(c) > 0


def test_boundary_aware_chunking_preserves_words():
    """Verify that boundary-aware chunking avoids splitting words across characters."""
    sample_text = (
        "FastAPI is a modern web framework. "
        "It provides high performance with Pydantic validation. "
        "Swagger documentation is automatically generated."
    )
    chunks = chunk_text(sample_text, chunk_size=50, chunk_overlap=15)
    assert len(chunks) >= 2

    # Check that chunks end cleanly on punctuation or complete words (no orphaned fragments)
    for chunk in chunks:
        assert not chunk.endswith("FastA")
        assert not chunk.endswith("fra")
        assert len(chunk) <= 50


def test_rag_ingest_and_retrieve():
    engine = RAGEngine(collection_name="test_knowledge")
    doc = (
        "PostgreSQL is a powerful, open source object-relational database system. "
        "It uses and extends the SQL language combined with many features that safely store and scale complex data workloads."
    )
    count = engine.ingest_document("pg_doc", doc, metadata={"category": "database"})
    assert count > 0

    results = engine.retrieve("open source relational database", top_k=1)
    assert len(results) >= 1
    assert "PostgreSQL" in results[0].text
    assert results[0].metadata["doc_id"] == "pg_doc"


def test_rag_metadata_filtering():
    """Verify that metadata filtering restricts vector retrieval to matching tags."""
    engine = RAGEngine(collection_name="test_metadata_filtering")

    engine.ingest_document(
        "postgres_doc",
        "PostgreSQL handles complex analytical queries and relational transactions.",
        metadata={"category": "database", "tier": "enterprise"},
    )
    engine.ingest_document(
        "fastapi_doc",
        "FastAPI handles high-speed asynchronous REST API endpoints and routing.",
        metadata={"category": "backend", "tier": "community"},
    )

    # Query for 'database' category
    db_results = engine.retrieve("database queries and transactions", top_k=5, where={"category": "database"})
    assert len(db_results) >= 1
    for r in db_results:
        assert r.metadata["category"] == "database"
        assert "PostgreSQL" in r.text

    # Query for 'backend' category
    be_results = engine.retrieve("asynchronous API endpoints and routing", top_k=5, where={"category": "backend"})
    assert len(be_results) >= 1
    for r in be_results:
        assert r.metadata["category"] == "backend"
        assert "FastAPI" in r.text


def test_rag_similarity_threshold_filtering():
    """Verify that chunks with cosine distance exceeding max_distance are excluded."""
    engine = RAGEngine(collection_name="test_threshold_filtering")
    engine.ingest_document("db_doc", "Relational database index optimization using B-trees.")

    # High threshold retains the matching document
    results_pass = engine.retrieve("database index", top_k=1, max_distance=0.9)
    assert len(results_pass) == 1

    # Overly strict threshold filters out the document
    results_drop = engine.retrieve("completely unrelated interstellar galaxy nebula space telescope", top_k=1, max_distance=0.01)
    assert len(results_drop) == 0


def test_answer_query_citations():
    engine = RAGEngine(collection_name="test_knowledge_qa")
    engine.ingest_document("test_doc", "Chroma is an AI-native open-source vector database.")

    response = engine.answer_query("What is Chroma?")
    assert "answer" in response
    assert len(response["sources"]) > 0
    assert "test_doc_chunk_0" in response["sources"][0]


def test_answer_query_out_of_domain_threshold_fallback():
    """Verify that out-of-scope queries cleanly trigger the refusal guardrail instead of hallucinating."""
    engine = RAGEngine(collection_name="test_out_of_domain")
    engine.ingest_document("python_doc", "Python is an interpreted programming language.")

    response = engine.answer_query(
        "What is the average temperature on the moons of Jupiter?",
        max_distance=0.001,  # Impose ultra-strict threshold to simulate complete irrelevance
    )
    assert response["answer"] == "No relevant context found in knowledge base."
    assert response["sources"] == []
