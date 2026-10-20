"""Topic 09: Document Q&A RAG Application (Complete Reference Solution).

Production-grade RAG pipeline featuring text chunking with semantic overlap,
ChromaDB vector indexing, metadata preservation, top-k semantic retrieval,
and grounded prompt synthesis.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import sys
from typing import Any
import chromadb
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TextChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None = None


def chunk_text(text: str, chunk_size: int = 200, chunk_overlap: int = 50) -> list[str]:
    """Split text into overlapping character chunks cleanly."""
    if not text.strip():
        return []
    if chunk_size <= chunk_overlap:
        raise ValueError("chunk_size must be strictly greater than chunk_overlap.")

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start += chunk_size - chunk_overlap

    return chunks


class RAGEngine:
    """Document Q&A engine using ChromaDB and LLM context synthesis."""

    def __init__(self, collection_name: str = "rag_knowledge") -> None:
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def ingest_document(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> int:
        """Chunk and ingest a text document into ChromaDB."""
        chunks = chunk_text(text)
        if not chunks:
            return 0

        meta_base = metadata or {}
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{**meta_base, "doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]

        self.collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )
        return len(chunks)

    def retrieve(self, query: str, top_k: int = 3) -> list[TextChunk]:
        """Query ChromaDB and return the top_k most similar chunks."""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        matched_chunks: list[TextChunk] = []
        if results and results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            ids = results["ids"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            dists = results["distances"][0] if "distances" in results and results["distances"] else [None] * len(docs)

            for doc_text, cid, meta, dist in zip(docs, ids, metas, dists):
                matched_chunks.append(
                    TextChunk(
                        chunk_id=cid,
                        text=doc_text,
                        metadata=meta,
                        distance=dist,
                    )
                )
        return matched_chunks

    def answer_query(self, query: str) -> dict[str, Any]:
        """Retrieve relevant context and synthesize a grounded answer."""
        retrieved_chunks = self.retrieve(query, top_k=3)
        if not retrieved_chunks:
            return {
                "query": query,
                "answer": "No relevant context found in knowledge base.",
                "sources": [],
            }

        context_str = "\n\n".join(
            [f"--- Document Source [{c.chunk_id}] ---\n{c.text}" for c in retrieved_chunks]
        )

        # Grounded prompt template
        system_instruction = (
            "You are a strict QA assistant. Answer the user query ONLY using the provided context snippets. "
            "If the answer cannot be found in the context, explicitly state that you do not know."
        )

        # In production or if API key available, call LLM; otherwise generate grounded reference
        groq_key = os.getenv("GROQ_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if groq_key or openai_key:
            from openai import OpenAI
            client = (
                OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key)
                if groq_key
                else OpenAI(api_key=openai_key)
            )
            model = "llama-3.3-70b-versatile" if groq_key else "gpt-4o-mini"
            messages = [
                {"role": "system", "content": f"{system_instruction}\n\nContext:\n{context_str}"},
                {"role": "user", "content": query},
            ]
            resp = client.chat.completions.create(model=model, messages=messages, temperature=0.0)
            answer_text = resp.choices[0].message.content or ""
        else:
            # Deterministic fallback answer for testing and offline environments
            answer_text = f"Synthesized answer based on {len(retrieved_chunks)} retrieved context chunks:\n{retrieved_chunks[0].text[:120]}..."

        return {
            "query": query,
            "answer": answer_text,
            "sources": [c.chunk_id for c in retrieved_chunks],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Document Q&A RAG Engine")
    parser.add_argument("query", nargs="?", default="What is LangGraph used for?")
    args = parser.parse_args()

    engine = RAGEngine()

    # Ingest sample knowledge
    doc1 = (
        "FastAPI is a modern, fast web framework for building APIs with Python 3.8+ based on standard Python type hints. "
        "It provides automatic interactive API documentation using Swagger UI and ReDoc. It is built on Starlette and Pydantic."
    )
    doc2 = (
        "LangGraph is a library for building stateful, multi-actor applications with LLMs, used to create agent and multi-agent workflows. "
        "Unlike standard linear chains, LangGraph allows adding cycles, branching, human-in-the-loop validation, and persistent memory checkpoints."
    )

    engine.ingest_document("fastapi_guide", doc1)
    engine.ingest_document("langgraph_guide", doc2)

    print(f"🔍 Asking RAG Engine: '{args.query}'\n")
    response = engine.answer_query(args.query)
    print(f"💡 Grounded Answer:\n{response['answer']}\n")
    print(f"📑 Sources Cited: {response['sources']}")


if __name__ == "__main__":
    main()
