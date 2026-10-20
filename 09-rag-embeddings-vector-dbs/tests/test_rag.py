"""Tests for Topic 09: RAG, Embeddings & Vector DBs."""

import sys
from pathlib import Path
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from rag_app import RAGEngine, chunk_text


def test_chunking_with_overlap():
    sample_text = "Python is an incredible language. It is widely used in artificial intelligence and machine learning."
    chunks = chunk_text(sample_text, chunk_size=40, chunk_overlap=10)
    assert len(chunks) > 1
    # Verify non-empty
    for c in chunks:
        assert len(c) > 0


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


def test_answer_query_citations():
    engine = RAGEngine(collection_name="test_knowledge_qa")
    engine.ingest_document("test_doc", "Chroma is an AI-native open-source vector database.")

    response = engine.answer_query("What is Chroma?")
    assert "answer" in response
    assert len(response["sources"]) > 0
    assert "test_doc_chunk_0" in response["sources"][0]
