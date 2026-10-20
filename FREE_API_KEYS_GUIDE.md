# 🔑 Complete Guide to 100% Free AI API Keys (Zero Cost Setup)

This repository is designed so that **anyone can learn AI engineering without paying a single dollar for API tokens or subscriptions**. You do **not** need an expensive OpenAI or Anthropic paid account to master all 10 topics and the final capstone project.

Below are the top 5 high-quality, completely free or generous-tier options for LLMs, embeddings, and fast inference.

---

## Quick Comparison Table

| Provider | Free Quota | Compatible SDK | Best Free Models | Where to Get |
| :--- | :--- | :--- | :--- | :--- |
| **Google AI Studio** | 15 RPM / 1M TPM free | Google GenAI / OpenAI SDK | `gemini-1.5-flash`, `gemini-2.0-flash` | [aistudio.google.com](https://aistudio.google.com/) |
| **Groq Cloud** | Generous daily RPM | OpenAI SDK / Groq SDK | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant` | [console.groq.com](https://console.groq.com/) |
| **OpenRouter** | 20+ Free models (`:free`) | OpenAI SDK | `meta-llama/llama-3.2-3b-instruct:free`, `google/gemini-2.0-flash-exp:free` | [openrouter.ai](https://openrouter.ai/) |
| **NVIDIA NIM** | 1,000 Free API credits | OpenAI SDK | `meta/llama-3.3-70b-instruct`, `deepseek-ai/deepseek-r1` | [build.nvidia.com](https://build.nvidia.com/) |
| **Ollama (Local)** | Unlimited (Runs offline) | OpenAI SDK / Ollama SDK | `llama3.2:3b`, `qwen2.5-coder:7b`, `nomic-embed-text` | [ollama.com](https://ollama.com/) |

---

## 1. Google AI Studio (Gemini) — *Recommended for RAG & Multimodal*

Google provides generous free-tier quotas through Google AI Studio without requiring a Google Cloud billing account or credit card.

### How to Get Your Key:
1. Navigate to **[https://aistudio.google.com/](https://aistudio.google.com/)**.
2. Sign in with any standard Google account.
3. Click **"Get API key"** in the top-left sidebar.
4. Click **"Create API key"** (in a new project or existing project).
5. Copy your key and add it to `.env`:
   ```env
   GEMINI_API_KEY="AIzaSy..."
   ```

### Python Quick Check:
```python
import os
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Explain why Python is essential for AI Engineers in 2 sentences.",
)
print(response.text)
```

---

## 2. Groq Cloud — *Recommended for Ultra-Fast Agent Tool Calling*

Groq provides blazing-fast inference (500+ tokens/second) on LPUs. Their free tier offers generous rate limits, ideal for fast iteration and tool-calling loops in LangChain & LangGraph.

### How to Get Your Key:
1. Navigate to **[https://console.groq.com/](https://console.groq.com/)**.
2. Sign in with your GitHub or Google account.
3. Go to **"API Keys"** in the left menu.
4. Click **"Create API Key"**, give it a name (e.g., `agentic-mastery`), and copy it.
5. Add it to `.env`:
   ```env
   GROQ_API_KEY="gsk_..."
   ```

### Python Quick Check (Standard OpenAI SDK Compatible!):
```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Hello Groq! What makes LPUs so fast?"}],
)
print(response.choices[0].message.content)
```

---

## 3. OpenRouter — *Gateway to 100+ Models (Including Free Tier)*

OpenRouter routes requests to dozens of model providers using a single OpenAI-compatible client. They feature models tagged with `:free` that cost \$0.00.

### How to Get Your Key:
1. Go to **[https://openrouter.ai/](https://openrouter.ai/)**.
2. Sign in with Google, GitHub, or Discord.
3. Go to **Keys** (`openrouter.ai/keys`) -> Click **"Create Key"**.
4. Free models you can use directly:
   - `meta-llama/llama-3.2-3b-instruct:free`
   - `meta-llama/llama-3.1-8b-instruct:free`
   - `google/gemini-2.0-flash-exp:free`
   - `mistralai/mistral-7b-instruct:free`
5. Add it to `.env`:
   ```env
   OPENROUTER_API_KEY="sk-or-v1-..."
   ```

### Python Quick Check:
```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

response = client.chat.completions.create(
    model="meta-llama/llama-3.2-3b-instruct:free",
    messages=[{"role": "user", "content": "Give me a one-line tip for writing clean Python code."}],
)
print(response.choices[0].message.content)
```

---

## 4. NVIDIA NIM (NVIDIA API Catalog) — *1,000 Free Credits*

NVIDIA offers 1,000 free inference credits on sign-up to test enterprise-grade models hosted on their cloud infrastructure.

### How to Get Your Key:
1. Navigate to **[https://build.nvidia.com/](https://build.nvidia.com/)**.
2. Create an account or sign in with your email.
3. Select any model (e.g. `meta/llama-3.3-70b-instruct` or `deepseek-ai/deepseek-r1`).
4. Click **"Get API Key"** on the model page.
5. Add it to `.env`:
   ```env
   NVIDIA_API_KEY="nvapi-..."
   ```

### Python Quick Check:
```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)

response = client.chat.completions.create(
    model="meta/llama-3.3-70b-instruct",
    messages=[{"role": "user", "content": "How does GPU tensor acceleration work in one paragraph?"}],
)
print(response.choices[0].message.content)
```

---

## 5. Ollama (Local AI) — *100% Free & Unlimited (Runs on your Laptop)*

If you have a laptop with an Apple Silicon (M1/M2/M3/M4) or a dedicated GPU (NVIDIA RTX / AMD), you can run models locally without any API key or internet access.

### Setup Instructions:
1. Download from **[https://ollama.com/download](https://ollama.com/download)**.
2. Install and open Ollama.
3. In your terminal, pull a model:
   ```bash
   # Fast, lightweight model (2 GB)
   ollama run llama3.2:3b

   # Coding specialist model (4.7 GB)
   ollama pull qwen2.5-coder:7b

   # High-quality embedding model for RAG (274 MB)
   ollama pull nomic-embed-text
   ```

### Python Quick Check (Standard OpenAI Compatible):
```python
from openai import OpenAI

# Ollama exposes an OpenAI-compatible endpoint at localhost:11434/v1
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama", # placeholder, not needed
)

response = client.chat.completions.create(
    model="llama3.2:3b",
    messages=[{"role": "user", "content": "Hello local AI!"}],
)
print(response.choices[0].message.content)
```

---

## Summary: Which One Should You Pick?

- **If you want the simplest, most generous free hosted setup:** Use **Google AI Studio (Gemini)** or **Groq Cloud**.
- **If you want maximum model variety:** Use **OpenRouter (Free tier)**.
- **If you have no internet or want total privacy:** Use **Ollama**.

In every topic module from Topic 7 through Topic 11, code templates include built-in support for **all** of these providers!
