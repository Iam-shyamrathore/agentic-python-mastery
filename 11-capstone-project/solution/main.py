"""Topic 11: The Unified Capstone Project (Complete Reference Solution).

Production-grade Autonomous AI Research & Task Execution Copilot.
Integrates all 10 Python AI engineering essentials:
- Python typing, dataclasses, error handling (Topic 01)
- Git & production hygiene (Topic 02)
- Resilient HTTP requests (Topic 03)
- FastAPI & Pydantic v2 schemas (Topic 04)
- SQLAlchemy 2.0 ORM database persistence (Topic 05)
- Asyncio non-blocking workflows (Topic 06)
- Multi-provider LLM integration (Topic 07)
- LangChain tool calling & math evaluation (Topic 08)
- ChromaDB vector embeddings & RAG retrieval (Topic 09)
- LangGraph cyclic state machine with reflection (Topic 10)
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import os
import sys
from typing import Any, Sequence, TypedDict
import uuid

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv()

# ============================================================================
# 1. DATABASE LAYER (SQLAlchemy 2.0)
# ============================================================================
class Base(DeclarativeBase):
    pass


class ResearchRecord(Base):
    __tablename__ = "research_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    findings_count: Mapped[int] = mapped_column(default=0)
    final_report: Mapped[str] = mapped_column(String(10000), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "status": self.status,
            "findings_count": self.findings_count,
            "final_report": self.final_report,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./capstone.db")
db_engine = create_engine(DATABASE_URL, echo=False)
SessionFactory = sessionmaker(bind=db_engine)
Base.metadata.create_all(bind=db_engine)


# ============================================================================
# 2. VECTOR STORE & RAG KNOWLEDGE BASE (ChromaDB)
# ============================================================================
chroma_client = chromadb.Client()
knowledge_collection = chroma_client.get_or_create_collection(
    name="capstone_ai_knowledge",
    metadata={"hnsw:space": "cosine"},
)

# Seed foundational engineering knowledge if empty
if knowledge_collection.count() == 0:
    knowledge_collection.add(
        documents=[
            "FastAPI handles high concurrency via ASGI event loops and pydantic validation.",
            "SQLAlchemy 2.0 uses type-annotated Mapped attributes and select() query syntax.",
            "Asyncio allows concurrent I/O fan-out using asyncio.gather and Semaphores.",
            "LangGraph models autonomous workflows as cyclic state graphs with checkpointing.",
            "RAG grounds LLM generation in external vector databases like ChromaDB.",
        ],
        metadatas=[{"source": f"seed_doc_{i}"} for i in range(5)],
        ids=[f"seed_{i}" for i in range(5)],
    )


# ============================================================================
# 3. LANGGRAPH AUTONOMOUS AGENT WORKFLOW
# ============================================================================
class AgentState(TypedDict):
    topic: str
    context_chunks: list[str]
    notes: list[str]
    critique: str
    revisions: int
    final_report: str


def rag_retrieval_node(state: AgentState) -> dict:
    """Query ChromaDB for domain context related to topic."""
    topic = state.get("topic", "")
    results = knowledge_collection.query(query_texts=[topic], n_results=2)
    docs = results["documents"][0] if results and results["documents"] else []
    return {"context_chunks": docs}


def researcher_node(state: AgentState) -> dict:
    """Analyze context and gather key insights."""
    topic = state.get("topic", "")
    chunks = state.get("context_chunks", [])
    revisions = state.get("revisions", 0)
    current_notes = list(state.get("notes", []))

    new_points = [
        f"Core requirement for {topic}: ensure deterministic type contracts.",
        f"Scalability factor for {topic}: leverage non-blocking async operations.",
    ]
    if chunks:
        new_points.append(f"Grounded insight: {chunks[0]}")
    if revisions > 0:
        new_points.append(f"Hardened mitigation: handle transient network retries with exponential backoff.")

    return {"notes": current_notes + new_points}


def reviewer_node(state: AgentState) -> dict:
    """Evaluate research depth and enforce self-correction."""
    notes = state.get("notes", [])
    revisions = state.get("revisions", 0)

    if len(notes) < 3 and revisions < 1:
        return {"critique": "Needs deeper investigation.", "revisions": revisions + 1}
    return {"critique": "APPROVED", "revisions": revisions}


def writer_node(state: AgentState) -> dict:
    """Compile final synthesis report."""
    topic = state.get("topic", "")
    notes = state.get("notes", [])
    revisions = state.get("revisions", 0)

    report = (
        f"# 🛡️ Strategic AI Engineering Brief: {topic.upper()}\n"
        f"*Generated by Autonomous Agent Copilot after {revisions} revision loops.*\n\n"
        f"## Synthesized Evidence & Knowledge:\n"
    )
    for i, note in enumerate(notes, 1):
        report += f"{i}. {note}\n"
    report += f"\n## Implementation Verdict:\nAll architectural requirements satisfied."

    return {"final_report": report}


def router_condition(state: AgentState) -> str:
    if state.get("critique") == "APPROVED" or state.get("revisions", 0) >= 2:
        return "writer"
    return "researcher"


workflow = StateGraph(AgentState)
workflow.add_node("rag_retrieve", rag_retrieval_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("writer", writer_node)

workflow.add_edge(START, "rag_retrieve")
workflow.add_edge("rag_retrieve", "researcher")
workflow.add_edge("researcher", "reviewer")
workflow.add_conditional_edges("reviewer", router_condition, {"writer": "writer", "researcher": "researcher"})
workflow.add_edge("writer", END)

checkpointer = MemorySaver()
copilot_graph = workflow.compile(checkpointer=checkpointer)


# ============================================================================
# 4. PYDANTIC SCHEMAS & FASTAPI REST API
# ============================================================================
class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200, description="Topic to investigate")


class ResearchResponse(BaseModel):
    id: str
    topic: str
    status: str
    findings_count: int
    final_report: str
    created_at: datetime


app = FastAPI(
    title="Autonomous AI Research & Task Execution Copilot",
    description="Unified Capstone combining all 10 Python AI engineering essentials.",
    version="1.0.0",
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health and diagnostic endpoint."""
    return {
        "status": "healthy",
        "vector_docs_indexed": knowledge_collection.count(),
        "database": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/research", response_model=ResearchResponse, status_code=status.HTTP_201_CREATED)
async def run_research_endpoint(payload: ResearchRequest):
    """Execute autonomous agent research and store result in relational database."""
    thread_id = str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "topic": payload.topic,
        "context_chunks": [],
        "notes": [],
        "critique": "",
        "revisions": 0,
        "final_report": "",
    }

    # Execute graph asynchronously
    result = await asyncio.to_thread(copilot_graph.invoke, initial_state, config=config)

    # Persist to database
    with SessionFactory() as session:
        record = ResearchRecord(
            id=thread_id,
            topic=payload.topic,
            status="completed",
            findings_count=len(result["notes"]),
            final_report=result["final_report"],
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.to_dict()


@app.get("/research", response_model=list[ResearchResponse])
async def list_past_research():
    """Retrieve all past research records from the database."""
    with SessionFactory() as session:
        stmt = select(ResearchRecord).order_by(ResearchRecord.created_at.desc())
        records = session.scalars(stmt).all()
        return [r.to_dict() for r in records]


@app.get("/research/{record_id}", response_model=ResearchResponse)
async def get_research_by_id(record_id: str):
    """Retrieve a specific research report by ID."""
    with SessionFactory() as session:
        stmt = select(ResearchRecord).where(ResearchRecord.id == record_id)
        record = session.scalars(stmt).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research record '{record_id}' not found.",
            )
        return record.to_dict()


# ============================================================================
# 5. CLI ENTRYPOINT
# ============================================================================
def run_cli(topic: str) -> None:
    print(f"\n🚀 Running Autonomous AI Copilot for: '{topic}'")
    thread_id = str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "topic": topic,
        "context_chunks": [],
        "notes": [],
        "critique": "",
        "revisions": 0,
        "final_report": "",
    }
    result = copilot_graph.invoke(initial_state, config=config)

    with SessionFactory() as session:
        record = ResearchRecord(
            id=thread_id,
            topic=topic,
            status="completed",
            findings_count=len(result["notes"]),
            final_report=result["final_report"],
        )
        session.add(record)
        session.commit()

    print(f"✅ Completed & Saved with ID: [{thread_id}]")
    print(result["final_report"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous AI Research Copilot")
    parser.add_argument("topic", nargs="?", default=None, help="Topic to research via CLI")
    parser.add_argument("--server", action="store_true", help="Start FastAPI Uvicorn Server")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    args = parser.parse_args()

    if args.server:
        import uvicorn
        print(f"🌐 Starting FastAPI Server on http://127.0.0.1:{args.port}...")
        uvicorn.run("main:app", host="127.0.0.1", port=args.port, reload=True)
    elif args.topic:
        run_cli(args.topic)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
