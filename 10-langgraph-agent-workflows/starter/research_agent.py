"""Topic 10: Stateful Research Assistant with LangGraph (Starter Template).

Complete each TODO section alongside your AI Assistant.
"""

from __future__ import annotations

from typing import TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph


class ResearchState(TypedDict):
    topic: str
    findings: list[str]
    critique: str
    revisions: int
    final_report: str


def researcher_node(state: ResearchState) -> dict:
    """Gather facts and notes on the topic."""
    # TODO: Populate findings based on state["topic"]
    raise NotImplementedError("Implement researcher_node")


def reviewer_node(state: ResearchState) -> dict:
    """Critique findings or approve."""
    # TODO: Critique findings, increment revisions if needed, or set critique to "APPROVED"
    raise NotImplementedError("Implement reviewer_node")


def writer_node(state: ResearchState) -> dict:
    """Synthesize findings into final comprehensive report."""
    # TODO: Compile final_report from findings
    raise NotImplementedError("Implement writer_node")


def should_continue(state: ResearchState) -> str:
    """Conditional edge router."""
    # TODO: Route to 'writer' if APPROVED or max revisions reached, else back to 'researcher'
    raise NotImplementedError("Implement should_continue")


def build_research_graph():
    """Compile the LangGraph workflow."""
    # TODO: Assemble StateGraph, add nodes, edges, conditional edges, and compile
    raise NotImplementedError("Implement build_research_graph")


def main() -> None:
    print("Welcome to Stateful Research Assistant! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
