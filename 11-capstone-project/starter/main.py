"""Topic 11: The Unified Capstone Project (Starter Template).

Complete each TODO section alongside your AI Assistant to build the
Autonomous AI Research & Task Execution Copilot.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, TypedDict
import uuid

import chromadb
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


# --- 1. Database Layer (SQLAlchemy 2.0) ---
class Base(DeclarativeBase):
    pass


class ResearchRecord(Base):
    __tablename__ = "research_records"

    # TODO: Define mapped columns for id, topic, status, findings, final_report, created_at
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed")
    final_report: Mapped[str] = mapped_column(String(5000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# --- 2. Pydantic API Schemas ---
class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200)


class ResearchResponse(BaseModel):
    id: str
    topic: str
    status: str
    final_report: str
    created_at: datetime


# --- 3. FastAPI Application ---
app = FastAPI(title="Autonomous AI Research Copilot", version="1.0.0")


@app.post("/research", response_model=ResearchResponse, status_code=status.HTTP_201_CREATED)
async def start_research(payload: ResearchRequest):
    """Execute autonomous research and store report in database."""
    # TODO: Connect ChromaDB RAG, run research workflow, persist to database, return response
    raise NotImplementedError("Implement research pipeline")


def main() -> None:
    print("Welcome to the Capstone Project! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
