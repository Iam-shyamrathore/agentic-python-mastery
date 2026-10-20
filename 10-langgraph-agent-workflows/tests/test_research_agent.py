"""Tests for Topic 10: LangGraph & Agent Workflows."""

from __future__ import annotations

from pathlib import Path
import sys
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from research_agent import (
    build_research_graph,
    get_sqlite_checkpointer,
    researcher_node,
    reviewer_node,
    should_continue,
    stream_research_workflow,
    writer_node,
)


def test_researcher_node():
    """Verify researcher node produces facts and respects pure node semantics."""
    state = {"topic": "FastAPI", "findings": [], "revisions": 0}
    res = researcher_node(state)
    assert len(res["findings"]) == 2
    assert "FastAPI" in res["findings"][0]


def test_reviewer_node_reflection():
    """Verify reviewer node triggers automated reflection when facts are sparse."""
    # Less than 4 findings requires revision
    state = {"topic": "FastAPI", "findings": ["1", "2"], "revisions": 0}
    res = reviewer_node(state)
    assert res["revisions"] == 1
    assert res["critique"] != "APPROVED"

    # 4 findings and revision done -> APPROVED
    state_done = {"topic": "FastAPI", "findings": ["1", "2", "3", "4"], "revisions": 1}
    res_done = reviewer_node(state_done)
    assert res_done["critique"] == "APPROVED"


def test_conditional_routing():
    """Verify conditional edge router enforces termination and iteration cycles."""
    assert should_continue({"critique": "APPROVED", "revisions": 1}) == "writer"
    assert should_continue({"critique": "Needs work", "revisions": 0}) == "researcher"
    assert should_continue({"critique": "Needs work", "revisions": 2}) == "writer"


def test_full_graph_execution():
    """Verify complete end-to-end autonomous graph run."""
    app = build_research_graph()
    initial_state = {
        "topic": "SQLAlchemy 2.0",
        "findings": [],
        "critique": "",
        "revisions": 0,
        "final_report": "",
        "status": "in_progress",
    }
    config = {"configurable": {"thread_id": "test_thread"}}
    output = app.invoke(initial_state, config=config)

    assert output["revisions"] >= 1
    assert len(output["findings"]) >= 4
    assert "SQLAlchemy 2.0" in output["final_report"]
    assert "Executive Research Report" in output["final_report"]
    assert output["status"] == "completed"


def test_human_in_the_loop_breakpoint():
    """Verify human-in-the-loop breakpoint halts before specified node and resumes cleanly."""
    # Compile with breakpoint before 'writer'
    app = build_research_graph(interrupt_before=["writer"])
    initial_state = {
        "topic": "Human-in-the-Loop Agents",
        "findings": [],
        "critique": "",
        "revisions": 0,
        "final_report": "",
        "status": "in_progress",
    }
    config = {"configurable": {"thread_id": "hitl_thread_101"}}

    # First invoke halts right before 'writer'
    output = app.invoke(initial_state, config=config)
    assert output.get("final_report", "") == ""

    # Check state snapshot shows graph is paused before 'writer'
    snapshot = app.get_state(config)
    assert snapshot.next == ("writer",)
    assert len(snapshot.values["findings"]) >= 4
    assert snapshot.values["critique"] == "APPROVED"

    # Resume graph execution by invoking with None
    resumed_output = app.invoke(None, config=config)
    assert "Executive Research Report" in resumed_output["final_report"]
    assert "Human-in-the-Loop Agents" in resumed_output["final_report"]
    assert resumed_output["status"] == "completed"

    # Check graph has completed
    after_snapshot = app.get_state(config)
    assert after_snapshot.next == ()


def test_streaming_node_updates():
    """Verify real-time streaming yields updates per node execution."""
    app = build_research_graph()
    initial_state = {
        "topic": "Streaming Graphs",
        "findings": [],
        "critique": "",
        "revisions": 0,
        "final_report": "",
        "status": "in_progress",
    }
    config = {"configurable": {"thread_id": "streaming_thread_202"}}

    streamed_nodes = []
    for node_name, updates in stream_research_workflow(app, initial_state, config):
        streamed_nodes.append(node_name)
        assert isinstance(updates, dict)

    assert "researcher" in streamed_nodes
    assert "reviewer" in streamed_nodes
    assert "writer" in streamed_nodes


def test_cycle_limit_prevents_infinite_loop():
    """Verify cycle limit guard prevents infinite loops on stubborn critique."""
    # State with unapproved critique but reached max revisions limit
    state_at_limit = {"critique": "Still not good enough", "revisions": 2}
    assert should_continue(state_at_limit) == "writer"

    state_beyond_limit = {"critique": "Needs more work", "revisions": 5}
    assert should_continue(state_beyond_limit) == "writer"


def test_sqlite_saver_checkpointing():
    """Verify persistent SQLite checkpointer restores state across executions."""
    saver = get_sqlite_checkpointer(":memory:")
    app = build_research_graph(checkpointer=saver)

    initial_state = {
        "topic": "SQLite Checkpointing",
        "findings": [],
        "critique": "",
        "revisions": 0,
        "final_report": "",
        "status": "in_progress",
    }
    config = {"configurable": {"thread_id": "sqlite_thread_303"}}

    output = app.invoke(initial_state, config=config)
    assert output["status"] == "completed"

    # Check that state is persisted in SQLite checkpointer
    persisted_state = app.get_state(config)
    assert persisted_state.values["topic"] == "SQLite Checkpointing"
    assert len(persisted_state.values["findings"]) >= 4
