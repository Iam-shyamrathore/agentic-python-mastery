# 🤖 Topic 07: LLM APIs & Prompting for AI Engineers

> **Master direct LLM API invocation, system prompts, structured Pydantic outputs, streaming responses, and free-tier multi-provider routing.**

---

## 🎯 Why This is the Core Skill of an AI Engineer

Calling an LLM is straightforward, but building production AI requires:
1. **Guaranteed Output Formats**: Real software cannot parse markdown code fences (` ```json `) reliably. We need strict schema enforcement.
2. **Provider Agility**: If OpenAI has an outage or Anthropic raises prices, your application must seamlessly switch to Groq, Gemini, or OpenRouter without rewriting application logic.
3. **Sub-second Latency**: Streaming tokens incrementally so users see responses immediately.

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. The Universal OpenAI-Compatible Interface

Almost all modern inference providers (Groq, OpenRouter, NVIDIA NIM, vLLM, Ollama) implement the standard OpenAI API specification:

```python
from openai import OpenAI
import os

# Connecting to Groq (Free Tier)
groq_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

# Connecting to OpenRouter (Free Tier)
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Connecting to Local Ollama (Zero Cost, No Key Needed)
ollama_client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)
```

---

### 2. Structured Outputs with Pydantic

Instead of begging the model ("Please output valid JSON only!"), modern APIs support schema enforcement:

```python
from pydantic import BaseModel, Field

class Step(BaseModel):
    step_number: int
    action: str
    estimated_minutes: int

class ProjectPlan(BaseModel):
    project_name: str
    steps: list[Step]

# Requesting structured output
response = groq_client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "You are a technical project planner."},
        {"role": "user", "content": "Plan building a RAG application in Python."}
    ],
    response_format={"type": "json_object"},
)
```

---

## 🛠️ The Hands-on Project: AI Text Assistant

In this module, you will build `starter/ai_assistant.py` featuring:
- Automatic detection of available API keys (Groq, Gemini, OpenRouter, Ollama)
- Text generation with streaming token output
- Structured response generation into typed Pydantic models
- Unit tests with mock fallback

### Running the Tests
```bash
pytest 07-llm-apis-prompting/tests/test_llm.py -v
```
