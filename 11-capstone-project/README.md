# 🏆 Topic 11: The Unified Capstone Project

## Autonomous AI Research & Task Execution Copilot

> **Unite all 10 Python AI engineering essentials into a production-grade, full-stack autonomous AI system.**

---

## 🏛️ System Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │                 CLIENTS                      │
                  │   - CLI Tool (`python cli.py`)               │
                  │   - REST API / Swagger UI (`/docs`)          │
                  └──────────────────────┬───────────────────────┘
                                         │ HTTP / JSON
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                        FASTAPI ASYNC APPLICATION CORE                          │
│                                                                                │
│  [Pydantic v2 Schemas] ◄────► [Dependency Injection & Auth/Env]                │
│                                        │                                       │
│                                        ▼                                       │
│                       [Async Background Worker Task]                           │
│                                        │                                       │
│                                        ▼                                       │
│               ┌────────────────────────────────────────────────┐               │
│               │             LANGGRAPH AGENT GRAPH              │               │
│               │                                                │               │
│               │  [START] ─► [RAG Retrieval] ─► [Tool Calling]  │               │
│               │                     ▲               │          │               │
│               │                     │ (Reflection)  ▼          │               │
│               │                     └───────── [Reviewer]      │               │
│               │                                     │          │               │
│               │                                     ▼          │               │
│               │                                 [Writer]       │               │
│               │                                     │          │               │
│               │                                   [END]        │               │
│               └────────────────────────┬───────────────────────┘               │
│                                        │                                       │
│                 ┌──────────────────────┴──────────────────────┐                │
│                 ▼                                             ▼                │
│     [ChromaDB Vector Store]                     [SQLAlchemy 2.0 Database]      │
│   Semantic Chunk Retrieval & Docs             Audit Log & Thread Checkpoints   │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🌟 How the 10 Essentials are Integrated

| Essential # | Topic | Concrete Role in Capstone |
| :-: | :--- | :--- |
| **01** | Python Essentials | Type hints, dataclasses, domain exceptions |
| **02** | Git & GitHub | Modular package design, secret leak prevention |
| **03** | HTTP & REST | Resilient client calls to external APIs with retry logic |
| **04** | FastAPI & Pydantic | Asynchronous REST API, request/response models |
| **05** | SQL & Database | SQLAlchemy 2.0 ORM storing execution logs in SQLite |
| **06** | Async Python | Async background job processing and non-blocking I/O |
| **07** | LLM APIs & Prompting | Provider router (Groq, Gemini, OpenRouter, Ollama) |
| **08** | LangChain Tools | Math calculator and system diagnostic tools |
| **09** | RAG & Vector DB | ChromaDB vector store indexing domain knowledge |
| **10** | LangGraph Workflows | Cyclic agent state graph with automated self-reflection |

---

## 🚀 Running the Capstone

### 1. Start the FastAPI Service
```bash
python 11-capstone-project/solution/app.py
```
Open your browser to `http://127.0.0.1:8000/docs` to test endpoints interactively via Swagger UI.

### 2. Run the CLI
```bash
python 11-capstone-project/solution/cli.py "Evaluate vector database options for RAG"
```

### 3. Run Automated Tests
```bash
pytest 11-capstone-project/tests/test_capstone.py -v
```
