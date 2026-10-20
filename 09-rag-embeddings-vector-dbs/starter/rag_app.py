"""Topic 09: Document Q&A RAG Application (Starter Template).

Complete each TODO section alongside your AI Assistant.
This starter template introduces you to production-grade Retrieval-Augmented Generation (RAG):
1. Boundary-aware semantic text chunking (no truncated words!).
2. High-dimensional vector spaces and distance metrics in ChromaDB.
3. Metadata filtering (`where={"category": "..."}`) for multi-tenant isolation.
4. Similarity threshold filtering (eliminating hallucination on out-of-domain queries).
5. Grounded prompt synthesis with verifiable source citations.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import logging
import os
import sys
from typing import Any
import chromadb

# Set up educational logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("starter_rag_app")


# ===========================================================================
# EDUCATIONAL GUIDE: Vector Spaces, Chunk Overlap & ChromaDB Persistence
# ===========================================================================
# 1. WHAT IS CHUNK OVERLAP & WHY IS IT ESSENTIAL?
#    When splitting documents into chunks of size N:
#    If a critical sentence ("Acme Corp acquired Beta Ltd for $50M on June 1st")
#    falls directly on the boundary between chunk 1 and chunk 2:
#    Without overlap: Chunk 1 gets "Acme Corp acquired Beta Ltd" and Chunk 2 gets
#    "for $50M on June 1st". Neither chunk has enough context to answer:
#    "How much did Acme Corp pay for Beta Ltd?"
#    With overlap (e.g. 50 characters): The boundary context is duplicated across
#    adjacent chunks, preserving relational facts and entity associations.
#
# 2. VECTOR SPACES & DISTANCE METRICS:
#    Vector embeddings are dense numerical vectors (e.g. 384, 768, or 1536 floats).
#    Common distance metrics configured via `metadata={"hnsw:space": ...}`:
#    - Cosine Distance ("cosine"): Measures angular difference regardless of vector magnitude.
#      Formula: 1 - (u . v) / (||u|| * ||v||).
#      Range [0, 2]. 0 = identical angle, 1 = orthogonal (unrelated), 2 = diametrically opposite.
#    - Euclidean Distance ("l2"): Straight-line geometric distance in n-dimensional space.
#    - Inner Product ("ip"): Dot product. Fast if vectors are pre-normalized to unit length.
#    In cosine space, chunks with distance > 0.8 are essentially random noise.
#    Filtering by distance prevents polluting LLM prompts on irrelevant queries!
#
# 3. IN-MEMORY VS. PERSISTENT CHROMADB:
#    - Ephemeral In-Memory: `chromadb.Client()`
#      Stores vectors in RAM. Perfect for fast unit testing and transient sessions.
#    - Persistent Storage: `chromadb.PersistentClient(path="./data/chroma_db")`
#      Persists HNSW vector graph and SQLite metadata to disk, so you don't need
#      to re-chunk and re-embed documents on every server restart.
# ===========================================================================


@dataclass
class TextChunk:
    """Represents an extracted chunk of text with metadata and vector distance."""

    chunk_id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None = None


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------
def chunk_text(
    text: str,
    chunk_size: int = 200,
    chunk_overlap: int = 50,
) -> list[str]:
    """Split text into boundary-aware overlapping chunks without cutting words in half.
    
    TODO:
    1. Validate: If `chunk_size <= chunk_overlap`, raise `ValueError`.
    2. Iterate through `text` from `start = 0` to `text_len`:
       - Take candidate slice `text[start : start + chunk_size]`.
       - Instead of hard cutting, scan backwards for natural boundaries:
         e.g. `\n\n`, `\n`, `. `, `! `, `? `, `; `, `, `, or ` ` (space).
       - Extract clean chunk string and append to `chunks`.
       - Compute `next_start = start + split_pos - chunk_overlap`.
       - If `next_start` falls inside a word, snap to the start of the word.
       - Ensure `next_start > start` to guarantee forward progress and avoid infinite loops!
    3. Return list of chunk strings.
    """
    raise NotImplementedError("Implement boundary-aware chunk_text")


# ---------------------------------------------------------------------------
# RAG Engine
# ---------------------------------------------------------------------------
class RAGEngine:
    """Document Q&A engine using ChromaDB and grounded context synthesis."""

    def __init__(self, collection_name: str = "rag_knowledge") -> None:
        """Initialize ChromaDB client and collection.
        
        TODO:
        1. Initialize `self.chroma_client = chromadb.Client()`.
           (For persistent storage in production, use `chromadb.PersistentClient(path=...)`).
        2. Create or get collection with cosine distance metric:
           `self.collection = self.chroma_client.get_or_create_collection(
               name=collection_name, metadata={"hnsw:space": "cosine"}
           )`
        """
        raise NotImplementedError("Implement __init__ Chroma collection creation")

    def ingest_document(
        self,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Chunk and ingest a text document into ChromaDB.
        
        TODO:
        1. Call `chunk_text(text)`.
        2. Build unique IDs: `ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]`.
        3. Build metadata dicts preserving doc_id and chunk_index:
           `metadatas = [{**(metadata or {}), "doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]`.
        4. Add to collection: `self.collection.add(documents=chunks, metadatas=metadatas, ids=ids)`.
        5. Return chunk count.
        """
        raise NotImplementedError("Implement ingest_document")

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        where: dict[str, Any] | None = None,
        max_distance: float | None = 0.8,
    ) -> list[TextChunk]:
        """Query ChromaDB with metadata filtering and similarity threshold filtering.
        
        TODO:
        1. Prepare query kwargs:
           `kwargs = {"query_texts": [query], "n_results": top_k}`
           If `where` is provided, include `kwargs["where"] = where`.
        2. Execute query: `results = self.collection.query(**kwargs)`.
        3. Iterate over returned documents, ids, metadatas, and distances.
        4. Filter out any chunk where `max_distance is not None and dist > max_distance`.
        5. Return list of `TextChunk` objects.
        """
        raise NotImplementedError("Implement retrieve with metadata and threshold filtering")

    def answer_query(
        self,
        query: str,
        top_k: int = 3,
        where: dict[str, Any] | None = None,
        max_distance: float | None = 0.8,
    ) -> dict[str, Any]:
        """Retrieve relevant context and synthesize a grounded answer.
        
        TODO:
        1. Call `retrieved_chunks = self.retrieve(query, top_k=top_k, where=where, max_distance=max_distance)`.
        2. If `not retrieved_chunks`:
           Return {"query": query, "answer": "No relevant context found in knowledge base.", "sources": []}.
        3. Format context string with chunk headers: `--- Document Source [{chunk_id}] ---\n{text}`.
        4. Build grounded prompt instructing LLM to answer strictly using context and cite sources.
        5. Call LLM (or synthesize grounded fallback if offline).
        6. Return `{"query": query, "answer": answer, "sources": [c.chunk_id for c in retrieved_chunks]}`.
        """
        raise NotImplementedError("Implement answer_query")


def main() -> None:
    print("Welcome to Document Q&A RAG Engine! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
