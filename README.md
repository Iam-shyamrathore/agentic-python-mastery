# 🧠 Agentic Python Mastery: The 0-to-100 Python Essentials for AI Engineers

> **"Don't just watch an instructor code. Pair program with your AI agent to master the exact Python stack needed to build modern AI applications."**

Welcome to the companion repository for the **Python Essentials for AI Engineers** video! Most Python courses dump 20 hours of generic syntax that has nothing to do with AI engineering. This repo is radically different.

Instead of passive video-watching, **every single folder in this repo contains an `AGENT_PROMPT.md` context document**. You simply feed that file into your favorite AI coding assistant (Cursor, Claude Code, Windsurf, Copilot, Cline, or Gemini Code Assist), and your agent transforms into an interactive, zero-to-100 senior AI mentor that guides you, quizzes you, reviews your code, and helps you build real-world mini-projects.

---

## 🗺️ The 10 Essentials Roadmap

| # | Topic | Core Focus | Hands-On Mini-Project | Status |
| :-: | :--- | :--- | :--- | :-: |
| **01** | [**Python Essentials**](./01-python-essentials/) | Data structures, typing, OOP, functional patterns, error handling | **CLI Task Manager** | ✅ Ready |
| **02** | [**Git & GitHub**](./02-git-and-github/) | Version control, branching strategies, PR workflows, agent commit conventions | **Version-Controlled Project** | ✅ Ready |
| **03** | [**HTTP, REST & APIs**](./03-http-rest-apis/) | Network protocols, JSON payloads, auth headers, pagination, error resilience | **API-Powered Data Fetcher** | ✅ Ready |
| **04** | [**FastAPI & Pydantic**](./04-fastapi-pydantic/) | Schema validation, dependency injection, async route handlers, OpenAPI docs | **Task Management API** | ✅ Ready |
| **05** | [**SQL & Database Connections**](./05-sql-database-connections/) | Relational modeling, SQLAlchemy 2.0 ORM, migrations, connection pools | **Persistent Task Tracker** | ✅ Ready |
| **06** | [**Async Python**](./06-async-python/) | Event loops, coroutines, `asyncio.gather`, semaphores, non-blocking I/O | **Concurrent API Fetcher** | ✅ Ready |
| **07** | [**LLM APIs & Prompting**](./07-llm-apis-prompting/) | System prompting, structured outputs, streaming, context windows, token counting | **AI Text Assistant** | ✅ Ready |
| **08** | [**LangChain & Tool Calling**](./08-langchain-tool-calling/) | LCEL (LangChain Expression Language), function binding, tool execution loops | **Tool-Using Assistant** | ✅ Ready |
| **09** | [**RAG, Embeddings & Vector DBs**](./09-rag-embeddings-vector-dbs/) | Chunking strategies, semantic embeddings, ChromaDB vector indexing, grounded QA | **Document Q&A Application** | ✅ Ready |
| **10** | [**LangGraph & Agent Workflows**](./10-langgraph-agent-workflows/) | Cyclic agent graphs, StateGraph, memory checkpoints, human-in-the-loop decisions | **Stateful Research Assistant** | ✅ Ready |
| **11** | [**Final Capstone Project**](./11-capstone-project/) | Unified autonomous agent combining FastAPI, Async, SQL, RAG & LangGraph | **Autonomous Research & Task Copilot** | 🏆 Capstone |

---

## ⚡ 100% Free Setup (No Paid Subscriptions Required!)

You do **not** need a paid OpenAI or Anthropic API subscription. All AI modules in this repository support free-tier providers:
- **Google AI Studio (Gemini)**: 15 requests/min completely free.
- **Groq Cloud**: Blazing-fast free LPU inference on Llama 3.3.
- **OpenRouter**: Access free models with `$0.00` tokens.
- **NVIDIA NIM**: 1,000 free API credits on sign-up.
- **Ollama**: Run 100% locally offline on your own machine.

👉 **See [FREE_API_KEYS_GUIDE.md](./FREE_API_KEYS_GUIDE.md) for step-by-step key acquisition instructions.**

---

## 🚀 How to Use This Repo with Your AI Coding Agent

This curriculum is designed to be completed inside an AI-native coding environment:

```
┌────────────────────────────────────────────────────────┐
│ 1. Open Folder in your AI Editor (e.g. Cursor / Claude)│
│                                                        │
│ 2. Feed the Agent Prompt:                              │
│    "@01-python-essentials/AGENT_PROMPT.md Let's start!"│
│                                                        │
│ 3. The AI teaches concepts, provides hints, and       │
│    reviews your code in the `starter/` directory.      │
│                                                        │
│ 4. Run `pytest` to verify your tests pass!             │
└────────────────────────────────────────────────────────┘
```

### Supported AI Editors & How to Feed Prompts:
- **Cursor**: Open the chat (`Cmd+L` or `Ctrl+L`), type `@01-python-essentials/AGENT_PROMPT.md I am ready to begin Topic 1. Guide me step by step.`
- **Claude Code (CLI)**: Run `claude "Read 01-python-essentials/AGENT_PROMPT.md and guide me through the curriculum."`
- **Windsurf (Cascade)**: Reference the `AGENT_PROMPT.md` file in Cascade chat and press enter.
- **GitHub Copilot / Roo Code / Cline**: Open `AGENT_PROMPT.md` in your active tab and instruct the assistant in chat.

---

## 📂 Standard Folder Anatomy

Every module follows an identical, predictable anatomy so you always know where you are:

```
XX-topic-name/
├── AGENT_PROMPT.md       <-- Feed this directly to your AI Assistant!
├── README.md             <-- Complete 0-to-100 comprehensive theory & syntax guide
├── starter/              <-- Scaffolded boilerplate with TODOs for you to code
│   └── ...
├── solution/             <-- Battle-tested reference implementation
│   └── ...
└── tests/                <-- Automated pytest suite to verify your solution
    └── ...
```

---

## 🛠️ Global Environment Setup

### 1. Clone the repository
```bash
git clone https://github.com/Iam-shyamrathore/agentic-python-mastery.git
cd agentic-python-mastery
```

### 2. Create and activate a Python virtual environment
```bash
# Using standard venv
python3 -m venv .venv

# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure your environment variables
```bash
cp .env.example .env
# Edit .env and paste your free Groq or Gemini API key
```

---

## 🎓 Learning Philosophy & Production Standards

1. **Active Retrieval over Passive Consumption**: You will write real code in `starter/`, make mistakes, run tests, and debug alongside your AI agent.
2. **Production Standards from Day 1**:
   - **No Toy Skeletons**: Every solution is hardened for production use with defensive error boundaries, logging, input sanitization, and graceful degradation.
   - **Explanatory Comments**: Code contains real architectural comments answering *why* a particular design pattern was chosen and what breaks in production if omitted.
   - **Type Safety**: Strictly enforced `typing` and Pydantic v2 schemas across all 11 modules.
   - **Automated Verification**: Complete test suites using `pytest` and `pytest-asyncio` so you and your agent can verify every milestone objectively.
3. **From Zero to Capstone**: Each topic builds directly on the previous one, culminating in an end-to-end production AI service in Topic 11.

---

## 🌟 Support & Community
If you found this video and repository helpful, give it a ⭐ on GitHub and share your progress!
