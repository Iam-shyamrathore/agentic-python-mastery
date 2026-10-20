# 🕸️ Topic 10: LangGraph & Agent Workflows for AI Engineers

> **Master stateful agent architectures, cyclic execution graphs, self-correction/reflection loops, and memory checkpointing with LangGraph.**

---

## 🎯 Why LangGraph is the Leading Framework for Autonomous Agents

Simple LangChain chains and legacy linear agents break when complex reasoning is required:
- They cannot self-correct when an initial tool fails
- They cannot perform iterative multi-step research
- They cannot pause to wait for human confirmation

**LangGraph** models agent workflows as explicit state machines / graphs:
- **State**: The single source of truth passed between nodes
- **Nodes**: Python functions or LLM calls that compute state updates
- **Edges & Conditional Edges**: Determine the next node to execute based on state (loops, branching, or termination)

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. StateGraph Architecture

```
                 START
                   │
                   ▼
             [Researcher]
                   │
                   ▼
              [Reviewer]
              /         \
   (Revision needed?)    (Approved!)
            /             \
           ▼               ▼
      [Re-draft]         [Writer]
           │               │
           └──────►────────┘
                           │
                          END
```

---

### 2. Defining State & Nodes

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END

class ResearchState(TypedDict):
    topic: str
    notes: list[str]
    critique: str
    revisions: int
    final_report: str

def researcher_node(state: ResearchState) -> dict:
    notes = [f"Point A about {state['topic']}", f"Point B about {state['topic']}"]
    return {"notes": notes}

def reviewer_node(state: ResearchState) -> dict:
    revisions = state.get("revisions", 0)
    if revisions < 1:
        return {"critique": "Needs more technical depth.", "revisions": revisions + 1}
    return {"critique": "APPROVED", "revisions": revisions}

def router_edge(state: ResearchState) -> str:
    if state["critique"] == "APPROVED":
        return "writer"
    return "researcher"
```

---

### 3. Compiling the Graph with Persistence

```python
from langgraph.checkpoint.memory import MemorySaver

workflow = StateGraph(ResearchState)
workflow.add_node("researcher", researcher_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("writer", writer_node)

workflow.add_edge(START, "researcher")
workflow.add_edge("researcher", "reviewer")
workflow.add_conditional_edges("reviewer", router_edge)
workflow.add_edge("writer", END)

checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)
```

---

## 🛠️ The Hands-on Project: Stateful Research Assistant

In this module, you will build `starter/research_agent.py`:
- Cyclic StateGraph workflow (Researcher -> Reviewer -> Writer)
- Conditional evaluation edge allowing automatic self-reflection and re-prompting
- Thread-level persistence with `MemorySaver`
- Automated test coverage

### Running the Tests
```bash
pytest 10-langgraph-agent-workflows/tests/test_research_agent.py -v
```
