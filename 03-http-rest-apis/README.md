# 🌐 Topic 03: HTTP, REST & APIs for AI Engineers

> **Master HTTP networking, connection pooling, HTTP/2 multiplexing, rate limit header handling, RFC 7231 Retry-After parsing, exponential backoff with jitter, and circuit breaker architecture for AI agents.**

---

## 🎯 Why HTTP & REST Mastery is Non-Negotiable for AI Engineers

Every real-world AI interaction travels across HTTP:
- Prompting an LLM (OpenAI, Anthropic, Gemini, Groq) is an `HTTP POST` carrying `Authorization: Bearer <key>` and streaming chunks (`text/event-stream`).
- Outbound tool calling (search APIs, database queries, calculators, weather endpoints) requires resilient client sessions.
- Ingestion pipelines for RAG continuously fetch articles, documentation, and raw data via web APIs.

If your HTTP client lacks connection pooling, timeout enforcement, `Retry-After` parsing, and circuit breakers, your agent will hang indefinitely, exhaust OS socket handles, or fail catastrophically under load.

---

## 💥 Production War Stories & Hard-Learned Lessons

### 💥 War Story 1: The 10,000 TCP Socket Exhaustion Outage
> **The Scenario:** A microservices team deployed an agent that performed web research using `requests.get(url)` inside a tight loop across 200 parallel worker threads:
> ```python
> # ❌ NAIVE IMPLEMENTATION:
> import requests
> for url in target_urls:
>     resp = requests.get(url)  # Fresh connection and TLS handshake every call!
> ```
> **The Incident:** Each `requests.get()` call created a new TCP socket, executed a full 3-way TCP handshake and TLS 1.3 negotiation (taking 120ms each), and then closed the connection. When connections are closed, the OS keeps sockets in the `TIME_WAIT` state for 60 seconds to catch delayed packets. Within 3 minutes, the Linux kernel exhausted its available ephemeral port range (`cat /proc/sys/net/ipv4/ip_local_port_range`), and all outbound networking failed with `OSError: [Errno 99] Cannot assign requested address`.
> 
> **The Fix:** Reuse an `httpx.Client` configured with connection pooling (`httpx.Limits(max_connections=100, max_keepalive_connections=20)`). This reuses warm TCP connections across sequential requests, eliminating socket leaks and slashing request latency by 70%.

---

### 💥 War Story 2: The "Thundering Herd" 429 Cascading Crash
> **The Scenario:** An evaluation pipeline ran 100 concurrent test cases against Anthropic's Claude 3.5 Sonnet. The quota was 40,000 Tokens Per Minute (TPM).
> 
> **The Incident:** As soon as batch tests crossed the token limit, Anthropic returned `429 Too Many Requests`. The client code had a simplistic retry loop:
> ```python
> # ❌ SLEEPING FOR A STATIC DURATION WITHOUT JITTER:
> if resp.status_code == 429:
>     time.sleep(2.0)
> ```
> Exactly 2.0 seconds later, all 100 threads retried simultaneously. This synchronized burst ("thundering herd") immediately slammed into the rate limiter again, resetting the penalty window and extending the outage for 45 minutes until tests timed out.
> 
> **The Fix:** Two-pronged defense:
> 1. Check and parse the `Retry-After` response header (seconds or RFC 7231 HTTP-date) to respect the provider's exact cooling-off period.
> 2. When calculating fallback exponential backoff, always add randomized **jitter** (`min(max_delay, base * 2^attempt) + uniform(0.05, 0.2)`). Jitter desynchronizes concurrent retries, spreading load evenly across time.

---

### 💥 War Story 3: The $5,000 Zombie Retry Storm (Why You Need a Circuit Breaker)
> **The Scenario:** An agent tool queried an external third-party vector database whose cluster experienced a complete hardware outage (returning continuous `503 Service Unavailable`).
> 
> **The Incident:** 500 queued user agent workflows encountered the 503 error. Because the client was configured to retry 5 times with backoff, each workflow spent 30 seconds repeatedly hammering the dead database cluster while consuming costly GPU execution slots on the application server. The infrastructure burned $5,000 in wasted container hours before engineers manually intervened.
> 
> **The Fix:** Implement the **Circuit Breaker** pattern. After 5 consecutive failures, the circuit breaker trips to `OPEN`. All subsequent calls fail fast immediately without making network calls. After a recovery timeout (e.g. 30s), it enters `HALF_OPEN` to test a single canary request, safely restoring traffic only when the downstream service recovers.

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. HTTP Status Codes Every AI Engineer Must Know

| Code | Meaning | AI Engineering Context | Correct Client Action |
| :--- | :--- | :--- | :--- |
| **200 OK** | Success | LLM completed generation or tool succeeded | Parse JSON / stream SSE chunks |
| **201 Created** | Created | Stored vector embedding or memory record | Extract created resource identifier |
| **400 Bad Request** | Schema Mismatch | Malformed JSON schema or bad tool args | Do NOT retry; log and fix input |
| **401 Unauthorized** | Auth Failed | Invalid, missing, or expired API key | Fast-fail and alert developer |
| **429 Too Many Requests** | Quota Exceeded | RPM or TPM limit hit | **Parse `Retry-After` header & backoff with jitter** |
| **500 Internal Error** | Provider Crash | Model inference server crashed | Retry with backoff or fallback to alternative model |
| **503 Service Unavailable** | Overloaded | Provider capacity limit reached | Back off or trip Circuit Breaker |

---

### 2. RFC 7231 / RFC 9110 `Retry-After` Parsing

Model APIs send the `Retry-After` header in one of two standard formats:
1. **Delta-seconds**: `Retry-After: 120` (Wait 120 seconds).
2. **HTTP-date**: `Retry-After: Wed, 21 Oct 2026 07:28:00 GMT` (Wait until the specified UTC timestamp).

```python
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

def parse_retry_after(header_value: str | None) -> float | None:
    if not header_value:
        return None
    cleaned = header_value.strip()
    try:
        return max(0.0, float(cleaned))
    except ValueError:
        pass
    try:
        target = parsedate_to_datetime(cleaned)
        now = datetime.now(timezone.utc)
        return max(0.0, (target - now).total_seconds())
    except Exception:
        return None
```

---

### 3. Connection Pooling & HTTP/2

```python
import httpx

limits = httpx.Limits(
    max_connections=100,             # Max concurrent active sockets
    max_keepalive_connections=20,     # Idle sockets kept warm in pool
    keepalive_expiry=30.0,            # Idle socket timeout
)

with httpx.Client(
    limits=limits,
    timeout=httpx.Timeout(10.0),
    headers={"User-Agent": "AgenticClient/1.0"},
) as client:
    response = client.get("https://api.example.com/v1/models")
```

---

## 🛠️ The Hands-on Project: Resilient API Fetcher

In this module, you will build `api_fetcher.py` to:
- Establish a connection-pooled HTTP client with custom headers
- Gracefully handle HTTP/2 negotiation
- Extract rate limit headers (`x-ratelimit-remaining`, `retry-after`)
- Automatically retry on 429 and 5xx errors using exponential backoff with jitter and `Retry-After`
- Protect downstream services using a 3-state Circuit Breaker (`CLOSED`, `OPEN`, `HALF_OPEN`)

### Running the Tests
```bash
pytest 03-http-rest-apis/tests/test_api_fetcher.py -v
```
