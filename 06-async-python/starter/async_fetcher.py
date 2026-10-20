"""Topic 06: Concurrent Async Fetcher (Starter Template).

Master high-throughput asynchronous Python, semaphore rate limiting,
timeout and cancellation handling, and batch orchestration.

=============================================================================
📚 CORE ASYNC CONCEPTS & MENTAL MODELS FOR AI ENGINEERS
=============================================================================
1. `asyncio.Semaphore(max_concurrency)`:
   When scraping web pages or calling LLM APIs (OpenAI, Anthropic), firing 100 requests
   simultaneously causes HTTP 429 (Rate Limit Exceeded) or OS "Too many open files" errors.
   A Semaphore acts as a token dispenser:
   ```python
   async with self.semaphore:
       # At most `max_concurrency` tasks can enter this block concurrently.
       # Other coroutines wait cooperatively without blocking the thread.
       response = await client.get(url)
   ```

2. TASK TIMEOUTS & CANCELLATION (`asyncio.wait_for`):
   Network requests can hang indefinitely due to dropped packets or overloaded servers.
   Wrap coroutines in `asyncio.wait_for(coro, timeout=seconds)`:
   - If the task exceeds the timeout, it raises `asyncio.TimeoutError` and cancels the coroutine.
   - If an agent workflow cancels a subagent, `asyncio.CancelledError` is raised.

3. `asyncio.gather(..., return_exceptions=True)`:
   By default, `return_exceptions=False` means that if ANY task raises an unhandled
   exception, `gather` halts and propagates that exception, abandoning sibling tasks.
   Setting `return_exceptions=True` catches errors and returns the `Exception` object
   in the results list, allowing you to gracefully process partial successes!

4. BATCHING FOR BACKPRESSURE:
   When handling 5,000 URLs, launching 5,000 tasks at once consumes massive RAM.
   Process tasks in partitioned chunks (e.g. batches of 10) to maintain predictable
   memory consumption and smooth network throughput.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
import logging
import time
from typing import Any
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("async_fetcher")


# ---------------------------------------------------------------------------
# STEP 1: Error Categorization & Result Schema
# ---------------------------------------------------------------------------
class FetchErrorCategory(str, Enum):
    """Classification of fetch failures."""
    NONE = "none"
    TIMEOUT = "timeout"
    CONNECTION = "connection_error"
    HTTP_STATUS = "http_status_error"
    CANCELLED = "cancelled"
    DECODE_ERROR = "decode_error"
    UNKNOWN = "unknown"


@dataclass
class AsyncFetchResponse:
    """Encapsulates the response or failure details of an async HTTP request."""
    url: str
    status_code: int
    data: Any
    latency_ms: float
    error: str | None = None
    error_category: FetchErrorCategory = FetchErrorCategory.NONE
    attempts: int = 1

    @property
    def is_success(self) -> bool:
        return self.error is None and 200 <= self.status_code < 300


# ---------------------------------------------------------------------------
# STEP 2: Concurrent Fetcher Class
# ---------------------------------------------------------------------------
class ConcurrentAsyncFetcher:
    """Fetches multiple URLs concurrently with concurrency bounds and error recovery."""

    def __init__(
        self,
        max_concurrency: int = 5,
        timeout_seconds: float = 10.0,
    ) -> None:
        """Initialize fetcher with max concurrency and timeout.

        HINT:
        1. Store `self.max_concurrency = max_concurrency`.
        2. Store `self.timeout_seconds = timeout_seconds`.
        3. Create `self.timeout = httpx.Timeout(timeout_seconds)`.
        4. Initialize `self.semaphore = asyncio.Semaphore(max_concurrency)`.
        """
        self.max_concurrency = max_concurrency
        self.timeout_seconds = timeout_seconds
        self.timeout = httpx.Timeout(timeout_seconds)
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def fetch_one(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> AsyncFetchResponse:
        """Fetch a single URL guarded by semaphore with timing and error categorization.

        HINT:
        1. Acquire semaphore: `async with self.semaphore:`
        2. Measure start time: `start = time.perf_counter()`
        3. Execute request with timeout:
           `response = await asyncio.wait_for(client.get(url), timeout=self.timeout_seconds)`
        4. Calculate latency: `latency = (time.perf_counter() - start) * 1000`
        5. Check `if response.is_error`: return response with `FetchErrorCategory.HTTP_STATUS`.
        6. Try decoding JSON: `data = response.json()` fallback to `response.text`.
        7. Return `AsyncFetchResponse(...)`.
        8. Catch specific exceptions:
           - `(asyncio.TimeoutError, httpx.TimeoutException)` -> category TIMEOUT
           - `asyncio.CancelledError` -> category CANCELLED
           - `(httpx.ConnectError, httpx.NetworkError)` -> category CONNECTION
           - `Exception` -> category UNKNOWN
        """
        # TODO: Implement fetch_one with semaphore and error categorization
        raise NotImplementedError("Implement fetch_one")

    async def fetch_all(
        self,
        urls: list[str],
        client: httpx.AsyncClient | None = None,
    ) -> list[AsyncFetchResponse]:
        """Fetch all URLs concurrently using asyncio.gather.

        HINT:
        1. If urls is empty, return [].
        2. If client is None, use `async with httpx.AsyncClient(timeout=self.timeout) as client:`.
        3. Create task list: `tasks = [self.fetch_one(client, u) for u in urls]`.
        4. Gather tasks: `results = await asyncio.gather(*tasks, return_exceptions=True)`.
        5. Iterate through results; if an item is an Exception, wrap in AsyncFetchResponse with error details.
        6. Return list of AsyncFetchResponse.
        """
        # TODO: Implement fetch_all
        raise NotImplementedError("Implement fetch_all")

    async def fetch_in_batches(
        self,
        urls: list[str],
        batch_size: int = 5,
        show_progress: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> list[AsyncFetchResponse]:
        """Partition URLs into batches to control memory and socket pressure.

        HINT:
        1. Slice urls into chunks of `batch_size`:
           `chunks = [urls[i:i + batch_size] for i in range(0, len(urls), batch_size)]`
        2. Loop over chunks and call `await self.fetch_all(chunk, client=client)`.
        3. Aggregate and return all responses.
        """
        # TODO: Implement fetch_in_batches
        raise NotImplementedError("Implement fetch_in_batches")


async def main() -> None:
    urls = [f"https://jsonplaceholder.typicode.com/posts/{i}" for i in range(1, 6)]
    print(f"Welcome to Concurrent Async Fetcher! Fetching {len(urls)} URLs...")
    fetcher = ConcurrentAsyncFetcher(max_concurrency=3)
    results = await fetcher.fetch_all(urls)
    for r in results:
        print(f"[{r.status_code}] {r.url} - {r.latency_ms:.1f}ms (error={r.error})")


if __name__ == "__main__":
    asyncio.run(main())
