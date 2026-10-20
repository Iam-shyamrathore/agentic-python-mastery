# ⚡ Topic 06: Async Python for AI Engineers

> **Master asynchronous programming, event loops, coroutines, `asyncio.gather`, semaphores, and high-throughput concurrent I/O.**

---

## 🎯 Why Asynchronous Python is Essential for AI Engineering

AI systems spend over 95% of their execution time waiting for network I/O:
- Waiting 2 to 10 seconds for an LLM response or streaming tokens
- Fetching 20 web search results or scraping 10 URLs in an autonomous agent
- Computing embeddings across 100 text chunks for a vector database

In synchronous code, running 20 LLM requests sequentially at 2 seconds each takes **40 seconds**.
With `asyncio` and concurrent fan-out, all 20 requests execute simultaneously in **2.2 seconds** (an 18x speedup).

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. The Core Async Triad: Coroutines, Tasks, and Event Loops

```python
import asyncio
import httpx

# 1. Coroutine function definition
async def fetch_llm_summary(prompt: str) -> str:
    # Non-blocking async sleep or HTTP call
    await asyncio.sleep(0.5)
    return f"Summary for '{prompt}'"

# 2. Running an entrypoint
async def main():
    # Sequential execution: takes 1.0s
    res1 = await fetch_llm_summary("What is RAG?")
    res2 = await fetch_llm_summary("What is LangGraph?")

asyncio.run(main())
```

---

### 2. Concurrent Fan-Out with `asyncio.gather`

```python
async def parallel_pipeline():
    prompts = [f"Topic {i}" for i in range(10)]

    # Creates coroutines and schedules them concurrently on the event loop
    results = await asyncio.gather(
        *(fetch_llm_summary(p) for p in prompts),
        return_exceptions=True  # Prevents one failure from canceling all others
    )
    return results
```

---

### 3. Rate Limiting with `asyncio.Semaphore`

Uncontrolled concurrency will trigger immediate `429 Too Many Requests` or crash local memory. Use an `asyncio.Semaphore` to cap max active in-flight requests.

```python
class ConcurrentFetcher:
    def __init__(self, max_concurrency: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def safe_fetch(self, client: httpx.AsyncClient, url: str) -> dict:
        async with self.semaphore:  # Only 5 requests can be inside this block concurrently!
            response = await client.get(url, timeout=10.0)
            return response.json()
```

---

## 🛠️ The Hands-on Project: Concurrent API Fetcher

In this module, you will build a high-performance concurrent fetcher in `starter/async_fetcher.py`:
- `AsyncDataFetcher` utilizing `httpx.AsyncClient`
- Concurrency limiting via `asyncio.Semaphore`
- Benchmark harness comparing sequential vs concurrent fetch performance
- Automated verification tests

### Running the Tests
```bash
pytest 06-async-python/tests/test_async_fetcher.py -v
```
