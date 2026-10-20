"""Topic 10: Stateful Research Assistant with LangGraph (Complete Reference Solution).

Production-grade LangGraph workflow demonstrating cyclic state graphs,
automated reflection/review loops, memory checkpointing, and final report synthesis.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

load_dotenv()


class ResearchState(TypedDict):
    topic: str
    findings: list[str]
    critique: str
    revisions: int
    final_report: str


def researcher_node(state: ResearchState) -> dict:
    """Gather facts and notes on the topic."""
    topic = state.get("topic", "AI Engineering")
    revisions = state.get("revisions", 0)
    current_findings = list(state.get("findings", []))

    if revisions == 0:
        new_findings = [
            f"{topic} core architectural patterns and design principles.",
            f"Key production considerations for {topic} systems.",
        ]
    else:
        new_findings = [
            f"Advanced edge-case mitigation strategies for {topic}.",
            f"Empirical latency and throughput benchmarking data for {topic}.",
        ]

    return {"findings": current_findings + new_findings}


def reviewer_node(state: ResearchState) -> dict:
    """Critique findings or approve for writing."""
    revisions = state.get("revisions", 0)
    findings = state.get("findings", [])

    # Self-reflection: if fewer than 4 findings or 0 revisions, request iteration
    if revisions < 1 or len(findings) < 4:
        return {
            "critique": "Draft requires deeper empirical benchmarking and edge-case analysis.",
            "revisions": revisions + 1,
        }
    return {
        "critique": "APPROVED",
        "revisions": revisions,
    }


def writer_node(state: ResearchState) -> dict:
    """Synthesize findings into final comprehensive report."""
    topic = state.get("topic", "")
    findings = state.get("findings", [])
    revisions = state.get("revisions", 0)

    report_lines = [
        f"# Executive Research Report: {topic.upper()}",
        f"*Completed after {revisions} revision cycles with automated reflection.*\n",
        "## Key Findings & Strategic Insights:",
    ]
    for idx, f in enumerate(findings, 1):
        report_lines.append(f"{idx}. {f}")

    report_lines.append("\n## Conclusion:")
    report_lines.append(f"The analysis confirms that mastering {topic} is critical for production reliability.")

    return {"final_report": "\n".join(report_lines)}


def should_continue(state: ResearchState) -> str:
    """Conditional edge router: loop back or proceed to writer."""
    if state.get("critique") == "APPROVED" or state.get("revisions", 0) >= 2:
        return "writer"
    return "researcher"


def build_research_graph():
    """Compile the LangGraph workflow."""
    workflow = StateGraph(ResearchState)

    workflow.add_node("researcher", researcher_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("writer", writer_node)

    workflow.add_edge(START, "researcher")
    workflow.add_edge("researcher", "reviewer")
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            "writer": "writer",
            "researcher": "researcher",
        },
    )
    workflow.add_edge("writer", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stateful LangGraph Research Assistant")
    parser.add_argument("topic", nargs="?", default="Asynchronous Python in AI Agent Pipelines")
    args = parser.parse_args()

    print(f"🔬 Starting LangGraph Research Workflow for: '{args.topic}'...\n")
    app = build_research_graph()

    config = {"configurable": {"thread_id": "session_001"}}
    initial_state = {
        "topic": args.topic,
        "findings": [],
        "critique": "",
        "revisions": 0,
        "final_report": "",
    }

    final_output = app.invoke(initial_state, config=config)

    print(f"🔄 Total Iterations: {final_output['revisions']}")
    print(f"📋 Findings Collected: {len(final_output['findings'])}")
    print(f"📝 Final Critique Status: {final_output['critique']}\n")
    print(final_output["final_report"])


if __name__ == "__main__":
    main()
