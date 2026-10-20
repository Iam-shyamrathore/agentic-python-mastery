# 🌐 Topic 03: HTTP, REST & APIs for AI Engineers

> **Master HTTP networking, REST client engineering, error resilience, rate limiting, and exponential backoff essential for AI agents.**

---

## 🎯 Why HTTP & REST Mastery is Non-Negotiable for AI Engineers

Every AI interaction in production is an HTTP conversation:
- Prompting an LLM (OpenAI, Anthropic, Gemini, Groq) is an `HTTP POST` request with `Authorization: Bearer <key>` and streaming SSE (`text/event-stream`).
- An AI Agent calling an external weather, database, or search tool makes outbound REST calls.
- Ingestion pipelines for RAG continuously fetch articles, PDFs, and documentation via web APIs.

If your HTTP client lacks connection timeouts, connection pooling, and retry logic, your AI agent will hang indefinitely or crash the moment an API encounters a momentary blip.

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. HTTP Status Codes Every AI Engineer Must Know

| Code | Meaning | AI Engineering Context | Correct Client Action |
| :--- | :--- | :--- | :--- |
| **200 OK** | Success | LLM returned completion or tool executed | Parse JSON / stream chunks |
| **201 Created** | Resource Created | Stored vector embedding or record | Extract new resource ID |
| **400 Bad Request** | Invalid Input | Malformed JSON schema or bad params | Do NOT retry; fix payload |
| **401 Unauthorized** | Auth Failed | Invalid/expired API key | Alert user to check `.env` |
| **404 Not Found** | Missing Resource | Endpoint or document does not exist | Handle gracefully or return fallback |
| **429 Too Many Requests** | Rate Limited | Token per minute (TPM) or RPM exceeded | **Wait & retry with backoff!** |
| **500 Internal Error** | Provider Crash | Model inference server error | Retry with backoff or fallback model |
| **503 Service Unavailable** | Overloaded | High server load or capacity ceiling | Retry with exponential backoff |

---

### 2. Exponential Backoff with Jitter

When an API responds with `429 Too Many Requests` or `503 Service Unavailable`, slamming the server immediately causes cascading failure. Instead, use exponential backoff:

$$\text{delay} = \min(\text{max\_delay}, \text{base} \times 2^{\text{attempt}}) + \text{jitter}$$

```python
import time
import random

def backoff_delay(attempt: int, base: float = 1.0, max_delay: float = 30.0) -> float:
    # 2^attempt backoff
    delay = min(max_delay, base * (2 ** attempt))
    # Add random jitter between 0.1s and 0.5s to prevent synchronized thundering herd
    jitter = random.uniform(0.1, 0.5)
    return delay + jitter
```

---

### 3. Modern Python HTTP: `httpx` vs `requests`

`httpx` is the modern standard for AI engineering because it supports both synchronous and asynchronous operations, HTTP/2, connection pooling, and strict timeouts.

```python
import httpx

# Reusing a Client manages a connection pool (avoids repeated TLS handshakes)
with httpx.Client(timeout=httpx.Timeout(connect=5.0, read=30.0)) as client:
    response = client.get("https://api.github.com/users/octocat")
    response.raise_for_status()
    data = response.json()
    print(data["name"])
```

---

## 🛠️ The Hands-on Project: API-Powered Data Fetcher

In this module, you will build a resilient data fetcher in `starter/api_fetcher.py` that:
- Connects to public endpoints (JSONPlaceholder / Open-Meteo)
- Enforces explicit timeouts and connection pooling
- Automatically retries on 429 and 5xx errors using exponential backoff
- Parses JSON directly into typed Pydantic or dataclass objects

### Running the Tests
```bash
pytest 03-http-rest-apis/tests/test_api_fetcher.py -v
```
