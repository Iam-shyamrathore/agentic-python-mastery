"""Topic 09: Document Q&A RAG Application (Starter Template).

Complete each TODO section alongside your AI Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import chromadb


@dataclass
class TextChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]


def chunk_text(text: str, chunk_size: int = 200, chunk_overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    # TODO: Implement chunking logic with overlap
    raise NotImplementedError("Implement chunk_text")


class RAGEngine:
    """Document Q&A engine using ChromaDB and LLM context synthesis."""

    def __init__(self, collection_name: str = "rag_knowledge") -> None:
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(name=collection_name)

    def ingest_document(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> int:
        """Chunk and ingest a text document into ChromaDB."""
        # TODO: Split document into chunks and add to self.collection
        raise NotImplementedError("Implement ingest_document")

    def retrieve(self, query: str, top_k: int = 3) -> list[TextChunk]:
        """Query ChromaDB and return the top_k most similar chunks."""
        # TODO: Query collection and map results to list of TextChunk
        raise NotImplementedError("Implement retrieve")

    def answer_query(self, query: str) -> dict[str, Any]:
        """Retrieve relevant context and synthesize a grounded answer."""
        # TODO: Retrieve chunks and format grounded response with citations
        raise NotImplementedError("Implement answer_query")


def main() -> None:
    print("Welcome to Document Q&A RAG Engine! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
