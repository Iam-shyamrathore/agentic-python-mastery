"""Topic 10: Stateful Research Assistant with LangGraph (Complete Reference Solution).

Production-grade LangGraph workflow demonstrating:
1. Cyclic StateGraph architecture with automated reflection & self-correction loops.
2. State channels and reducers via Annotated[list[str], operator.add].
3. Human-in-the-loop (HITL) breakpoints using interrupt_before and state resumption.
4. Streaming node updates for real-time UI/CLI feedback.
5. Rich visual formatting of state transitions and executive report generation.
6. Defensive node validation and recursion limit guards to prevent infinite cycles.
7. Dual checkpoint persistence: MemorySaver (fast in-memory) and SqliteSaver (durable SQLite).

Why State Reducers Matter (Annotated[list, operator.add]):
---------------------------------------------------------
In LangGraph, the agent state is a typed schema (TypedDict). By default, keys use
replacement semantics (operator.setitem). If a node returns {"findings": ["Point C"]},
LangGraph replaces the entire list of findings with the single new item, erasing all
prior research!
By annotating `findings: Annotated[list[str], operator.add]`, we define a reducer
function (`operator.add`). LangGraph now appends new items to the existing list:
    state["findings"] = existing_findings + new_findings
This maintains purity: nodes return *only* the new delta items they discovered,
without mutating the incoming state dict in-place.
"""

from __future__ import annotations

import argparse
import operator
import os
import sqlite3
import sys
from typing import Annotated, Any, Iterator, Sequence, TypedDict

from dotenv import load_dotenv
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

load_dotenv()

console = Console()

# Safety recursion & iteration constants
DEFAULT_MAX_REVISIONS = 2
ABSOLUTE_CYCLE_LIMIT = 5


# ============================================================================
# 1. STATE DEFINITION & REDUCERS
# ============================================================================
class ResearchState(TypedDict):
    """The central state schema for the iterative research assistant.

    Attributes:
        topic: The primary research subject under investigation.
        findings: Accumulated list of verified facts. Annotated with `operator.add`
            reducer so each node yields only *new* findings, which LangGraph
            appends to the accumulated channel rather than overwriting.
        critique: Feedback from the reviewer node (e.g. 'APPROVED' or revision advice).
        revisions: Counter tracking reflection iterations to enforce termination.
        final_report: The synthesized executive summary in Markdown format.
        status: Current workflow status ('in_progress', 'interrupted', 'completed').
    """

    topic: str
    findings: Annotated[list[str], operator.add]
    critique: str
    revisions: int
    final_report: str
    status: str


# ============================================================================
# 2. PURE AGENT NODES WITH DEFENSIVE VALIDATION
# ============================================================================
def researcher_node(state: ResearchState) -> dict[str, Any]:
    """Gather domain knowledge and facts on the requested topic.

    Node Purity & State Reducers:
    -----------------------------
    Notice this node does NOT mutate `state["findings"]` in-place.
    Instead, it returns a dictionary containing *only* the newly discovered
    findings (`{"findings": new_findings}`). Because `findings` is annotated
    with `operator.add`, LangGraph's channel automatically concatenates:
        accumulated_findings = current_findings + new_findings

    If we omitted the reducer and returned `{"findings": new_findings}`,
    LangGraph's default `operator.setitem` would overwrite previous findings!

    Args:
        state: Current ResearchState dictionary.

    Returns:
        A delta dictionary updating `findings` and `status`.
    """
    topic = str(state.get("topic") or "Autonomous AI Systems").strip()
    if not topic:
        topic = "Autonomous AI Systems"

    revisions = int(state.get("revisions", 0) or 0)

    # Simulate progressive fact gathering across iterative cycles
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

    return {
        "findings": new_findings,
        "status": "in_progress",
    }


def reviewer_node(state: ResearchState) -> dict[str, Any]:
    """Critique findings against quality benchmarks or approve for synthesis.

    Implements the automated reflection / self-correction loop:
    - If findings are insufficient (< 4 facts) or revision count is low,
      it requests an iteration cycle with targeted critique.
    - If criteria are met, it sets critique to 'APPROVED'.

    Args:
        state: Current ResearchState dictionary.

    Returns:
        A delta dictionary updating `critique`, `revisions`, and `status`.
    """
    revisions = int(state.get("revisions", 0) or 0)
    findings = state.get("findings") or []

    # Defensive check: ensure findings is a sequence
    if not isinstance(findings, (list, tuple)):
        findings = [str(findings)]

    # Self-reflection gate: Require at least 1 revision loop AND at least 4 findings
    if revisions < 1 or len(findings) < 4:
        return {
            "critique": "Draft requires deeper empirical benchmarking and edge-case analysis.",
            "revisions": revisions + 1,
            "status": "in_progress",
        }

    return {
        "critique": "APPROVED",
        "revisions": revisions,
        "status": "in_progress",
    }


def writer_node(state: ResearchState) -> dict[str, Any]:
    """Synthesize accumulated findings into a polished executive report.

    Args:
        state: Current ResearchState dictionary.

    Returns:
        A delta dictionary setting `final_report` and marking `status='completed'`.
    """
    topic = str(state.get("topic") or "Autonomous AI Systems").strip()
    findings = list(state.get("findings") or [])
    revisions = int(state.get("revisions", 0) or 0)

    report_lines = [
        f"# Executive Research Report: {topic.upper()}",
        f"*Completed after {revisions} revision cycles with automated reflection.*\n",
        "## Key Findings & Strategic Insights:",
    ]

    if not findings:
        report_lines.append("1. Baseline architectural investigation initiated (no findings recorded).")
    else:
        for idx, fact in enumerate(findings, 1):
            report_lines.append(f"{idx}. {fact}")

    report_lines.append("\n## Architectural Conclusion:")
    report_lines.append(
        f"Mastery of {topic} is critical for production reliability, horizontal scaling, "
        "and resilient autonomous workflow orchestration."
    )

    return {
        "final_report": "\n".join(report_lines),
        "status": "completed",
    }


# ============================================================================
# 3. CONDITIONAL ROUTING & CYCLE SAFETY
# ============================================================================
def should_continue(state: ResearchState) -> str:
    """Conditional edge router: determines next node in cyclic graph.

    Cycle Safety Guardrails:
    ------------------------
    Without explicit iteration ceilings, cyclic graphs risk infinite loops
    when reflection criteria fail to converge (consuming tokens and CPU).
    We enforce a strict cycle limit (`DEFAULT_MAX_REVISIONS`). If revisions
    reach or exceed this threshold, the graph terminates into `writer`.

    Args:
        state: Current ResearchState dictionary.

    Returns:
        The name of the next node: 'writer' or 'researcher'.
    """
    critique = state.get("critique", "")
    revisions = int(state.get("revisions", 0) or 0)

    # Route to writer if explicitly approved or if cycle limit reached
    if critique == "APPROVED" or revisions >= DEFAULT_MAX_REVISIONS:
        return "writer"

    return "researcher"


# ============================================================================
# 4. GRAPH ASSEMBLY & PERSISTENCE CONFIGURATION
# ============================================================================
def get_sqlite_checkpointer(db_path: str = "checkpoints.db") -> SqliteSaver:
    """Create a persistent SQLite checkpointer for durable agent memory.

    Args:
        db_path: Path to the SQLite database file or ':memory:'.

    Returns:
        Initialized and migrated SqliteSaver instance.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    return saver


def build_research_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    interrupt_before: Sequence[str] | None = None,
) -> CompiledStateGraph:
    """Compile the LangGraph research workflow with cyclic control flow.

    Args:
        checkpointer: Checkpoint saver for state persistence and HITL.
            Defaults to `MemorySaver()` if not provided.
        interrupt_before: Optional sequence of node names to pause execution before,
            enabling Human-in-the-Loop inspection, approval, or modification.
            Example: `interrupt_before=["writer"]`.

    Returns:
        CompiledStateGraph executable.
    """
    workflow = StateGraph(ResearchState)

    # 1. Register pure nodes
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("writer", writer_node)

    # 2. Add control-flow edges
    workflow.add_edge(START, "researcher")
    workflow.add_edge("researcher", "reviewer")

    # 3. Add dynamic conditional edge
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            "writer": "writer",
            "researcher": "researcher",
        },
    )

    # 4. Final edge to END
    workflow.add_edge("writer", END)

    # 5. Checkpointer is required for state inspection, resumption, and HITL
    if checkpointer is None:
        checkpointer = MemorySaver()

    # 6. Compile graph with checkpointer and optional breakpoint interrupts
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before,
    )


# ============================================================================
# 5. STREAMING & RICH VISUALIZATION
# ============================================================================
def stream_research_workflow(
    app: CompiledStateGraph,
    initial_state: dict[str, Any],
    config: dict[str, Any],
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Stream real-time state updates as each node executes in the graph.

    Yields:
        Tuples of (node_name, update_dict) for every node transition.
    """
    for event in app.stream(initial_state, config=config, stream_mode="updates"):
        for node_name, updates in event.items():
            yield node_name, updates


def format_state_transition(node_name: str, updates: dict[str, Any]) -> None:
    """Render a styled terminal panel for a state transition."""
    color_map = {
        "researcher": "cyan",
        "reviewer": "yellow",
        "writer": "green",
    }
    color = color_map.get(node_name, "magenta")

    details = []
    if "findings" in updates:
        details.append(f"[bold]New Findings Added:[/bold] {len(updates['findings'])}")
        for f in updates["findings"]:
            details.append(f"  • [italic]{f}[/italic]")
    if "critique" in updates:
        status_style = "bold green" if updates["critique"] == "APPROVED" else "bold yellow"
        details.append(f"[bold]Critique:[/bold] [{status_style}]{updates['critique']}[/{status_style}]")
    if "revisions" in updates:
        details.append(f"[bold]Revision Cycle:[/bold] {updates['revisions']}")
    if "final_report" in updates:
        details.append("[bold]Final Report Generated:[/bold] [green]Complete[/green]")

    content = "\n".join(details)
    console.print(
        Panel(
            content,
            title=f"[{color}]Node Transition: [bold]{node_name.upper()}[/bold][/{color}]",
            border_style=color,
            expand=False,
        )
    )


# ============================================================================
# 6. CLI ENTRYPOINT WITH HITL & STREAMING
# ============================================================================
def run_cli(topic: str, enable_hitl: bool = False, use_sqlite: bool = False) -> None:
    """Run interactive research assistant from command line."""
    console.print(
        Panel(
            f"[bold cyan]LangGraph Autonomous Research Assistant[/bold cyan]\n"
            f"[dim]Topic:[/dim] [bold]{topic}[/bold]\n"
            f"[dim]Human-in-the-Loop:[/dim] {'[green]Enabled (pause before writer)[/green]' if enable_hitl else '[yellow]Disabled (autonomous)[/yellow]'}\n"
            f"[dim]Persistence:[/dim] {'[cyan]SQLite (checkpoints.db)[/cyan]' if use_sqlite else '[blue]MemorySaver[/blue]'}",
            title="🔬 Workflow Initialization",
            border_style="cyan",
        )
    )

    checkpointer = get_sqlite_checkpointer("research_checkpoints.db") if use_sqlite else MemorySaver()
    interrupt_before = ["writer"] if enable_hitl else None
    app = build_research_graph(checkpointer=checkpointer, interrupt_before=interrupt_before)

    thread_id = "cli_session_001"
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 25,
    }

    initial_state = {
        "topic": topic,
        "findings": [],
        "critique": "",
        "revisions": 0,
        "final_report": "",
        "status": "in_progress",
    }

    console.print("\n[bold]Streaming Node Executions:[/bold]")
    for node_name, updates in stream_research_workflow(app, initial_state, config):
        format_state_transition(node_name, updates)

    # Handle Human-in-the-Loop breakpoint if enabled
    if enable_hitl:
        state_snapshot = app.get_state(config)
        if state_snapshot.next and "writer" in state_snapshot.next:
            console.print(
                Panel(
                    f"[bold yellow]⏸️ Graph paused at Human-in-the-Loop breakpoint before node: 'writer'[/bold yellow]\n\n"
                    f"Current accumulated findings: [bold]{len(state_snapshot.values.get('findings', []))}[/bold]\n"
                    f"Critique status: [bold green]{state_snapshot.values.get('critique', '')}[/bold green]\n\n"
                    f"Press [bold green]Enter[/bold green] to approve and resume report synthesis...",
                    title="Human Approval Required",
                    border_style="yellow",
                )
            )
            # In interactive CLI, prompt user:
            try:
                input()
            except EOFError:
                pass

            console.print("[dim]Resuming graph execution with human approval...[/dim]")
            for node_name, updates in app.stream(None, config=config, stream_mode="updates"):
                for n_name, upd in node_name.items() if isinstance(node_name, dict) else [(node_name, updates)]:
                    format_state_transition(n_name, upd)

    # Fetch final state snapshot
    final_state = app.get_state(config).values

    # Display summary table
    table = Table(title="Execution Summary", border_style="dim")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold")
    table.add_row("Total Revision Cycles", str(final_state.get("revisions", 0)))
    table.add_row("Total Accumulated Findings", str(len(final_state.get("findings", []))))
    table.add_row("Final Critique", str(final_state.get("critique", "")))
    table.add_row("Status", str(final_state.get("status", "")))
    console.print(table)

    # Pretty-print final executive report
    if final_state.get("final_report"):
        console.print(
            Panel(
                final_state["final_report"],
                title="📄 Synthesized Executive Report",
                border_style="green",
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stateful LangGraph Research Assistant")
    parser.add_argument("topic", nargs="?", default="Asynchronous Python in AI Agent Pipelines")
    parser.add_argument("--hitl", action="store_true", help="Enable Human-in-the-loop approval breakpoint before writer")
    parser.add_argument("--sqlite", action="store_true", help="Persist checkpoints to SQLite rather than memory")
    args = parser.parse_args()

    run_cli(topic=args.topic, enable_hitl=args.hitl, use_sqlite=args.sqlite)


if __name__ == "__main__":
    main()
