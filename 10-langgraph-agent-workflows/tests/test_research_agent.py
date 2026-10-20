"""Tests for Topic 10: LangGraph & Agent Workflows."""

import sys
from pathlib import Path
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from research_agent import (
    build_research_graph,
    researcher_node,
    reviewer_node,
    should_continue,
    writer_node,
)


def test_researcher_node():
    state = {"topic": "FastAPI", "findings": [], "revisions": 0}
    res = researcher_node(state)
    assert len(res["findings"]) == 2
    assert "FastAPI" in res["findings"][0]


def test_reviewer_node_reflection():
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
    assert should_continue({"critique": "APPROVED", "revisions": 1}) == "writer"
    assert should_continue({"critique": "Needs work", "revisions": 0}) == "researcher"
    assert should_continue({"critique": "Needs work", "revisions": 2}) == "writer"


def test_full_graph_execution():
    app = build_research_graph()
    initial_state = {
        "topic": "SQLAlchemy 2.0",
        "findings": [],
        "critique": "",
        "revisions": 0,
        "final_report": "",
    }
    config = {"configurable": {"thread_id": "test_thread"}}
    output = app.invoke(initial_state, config=config)

    assert output["revisions"] >= 1
    assert len(output["findings"]) >= 4
    assert "SQLAlchemy 2.0" in output["final_report"]
    assert "Executive Research Report" in output["final_report"]
