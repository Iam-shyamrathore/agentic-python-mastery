"""Topic 06: Concurrent Async Fetcher (Complete Reference Solution).

Production-grade asynchronous I/O engine demonstrating:
- Bounded concurrency with `asyncio.Semaphore`
- Task-level cancellation and timeout boundaries (`asyncio.wait_for`)
- Fine-grained error categorization (timeouts, DNS/network, HTTP errors, cancellations)
- Batch execution with `rich` progress tracking and structured logging
- Resilient recovery from partial failures
- Educational breakdown of event loop internals and CPU vs I/O offloading.

=============================================================================
📚 EVENT LOOP MECHANICS & ASYNC ARCHITECTURE FOR AI ENGINEERS
=============================================================================

1. HOW THE EVENT LOOP WORKS UNDER THE HOOD:
   Python's `asyncio` runs on a single OS thread using cooperative multitasking.
   At its core is an OS kernel event multiplexer:
   - Linux: `epoll`
   - macOS / BSD: `kqueue`
   - Windows: `IOCP` (I/O Completion Ports)

   When an async coroutine calls `await client.get(url)`:
   a) The underlying TCP socket is set to non-blocking mode (`O_NONBLOCK`).
   b) A read/write file descriptor is registered with the kernel multiplexer (`kqueue`/`epoll`).
   c) The coroutine pauses and yields control back to the event loop.
   d) The event loop immediately executes other runnable coroutines.
   e) When the kernel signals that network packets have arrived on that socket, the event
      loop wakes up the paused coroutine and resumes execution.

2. CPU-BOUND vs. I/O-BOUND TASKS IN AI SYSTEMS:
   - I/O-Bound (Cooperative Async is Ideal):
     * Streaming completion tokens from Anthropic / OpenAI / Ollama.
     * Vector database similarity queries (Pinecone, ChromaDB, Qdrant).
     * Relational database queries over TCP.
     * Web scraping / web search API queries (Tavily, Firecrawl, Serper).
     These tasks spend 95%+ of their time waiting on network packets. 10,000 I/O
     tasks can be multiplexed concurrently on a single thread!

   - CPU-Bound (Cooperative Async is DANGEROUS):
     * Token counting (e.g. `tiktoken.encode(prompt)` over a 50k-word book).
     * Vector math / cosine similarity computed on large NumPy matrices.
     * Complex Pydantic schema validation over 10MB JSON documents.
     * Embedding tensor operations and local ML model execution.
     WARNING: Because Python's event loop runs on a single thread, executing CPU-heavy
     code inside an `async def` function BLOCKS THE ENTIRE EVENT LOOP! No other user
     requests, health checks, or streaming tokens can be processed until the CPU finishes.

   - The Solution for CPU-bound tasks in async services:
     Offload CPU work to worker threads or processes:
     `await asyncio.to_thread(cpu_heavy_token_counting, text)` or
     `loop.run_in_executor(process_pool, cpu_matrix_multiplication, mat_a, mat_b)`.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from enum import Enum
import logging
import time
from typing import Any, Callable, Sequence
import httpx

# ---------------------------------------------------------------------------
# Structured Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [async_fetcher] %(message)s",
)
logger = logging.getLogger("async_fetcher")


# ---------------------------------------------------------------------------
# Error Categorization Enum
# ---------------------------------------------------------------------------
class FetchErrorCategory(str, Enum):
    """Categorization of asynchronous fetch failures for observability and retry policies."""
    NONE = "none"
    TIMEOUT = "timeout"
    CONNECTION = "connection_error"
    HTTP_STATUS = "http_status_error"
    CANCELLED = "cancelled"
    DECODE_ERROR = "decode_error"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Typed Result Envelope
# ---------------------------------------------------------------------------
@dataclass
class AsyncFetchResponse:
    """Encapsulates the result of a single asynchronous HTTP fetch."""
    url: str
    status_code: int
    data: Any
    latency_ms: float
    error: str | None = None
    error_category: FetchErrorCategory = FetchErrorCategory.NONE
    attempts: int = 1

    @property
    def is_success(self) -> bool:
        """Return True if the request completed with HTTP 2xx and no errors."""
        return self.error is None and 200 <= self.status_code < 300


# ---------------------------------------------------------------------------
# Concurrent Async Fetcher Engine
# ---------------------------------------------------------------------------
class ConcurrentAsyncFetcher:
    """High-throughput asynchronous HTTP fetcher with concurrency regulation,

    per-task timeout boundaries, structured error categorization, and batching.
    """

    def __init__(
        self,
        max_concurrency: int = 5,
        timeout_seconds: float = 10.0,
    ) -> None:
        """Initialize fetcher with concurrency limits and timeouts.

        Args:
            max_concurrency: Max simultaneous requests allowed in flight at once.
            timeout_seconds: Hard timeout per request (both connection and read).
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
        """Fetch a single URL guarded by a concurrency semaphore and timeout boundary.

        Args:
            client: Shared `httpx.AsyncClient` reusing connection pools.
            url: Target web address to fetch.

        Returns:
            AsyncFetchResponse with latency metrics and error categorization.
        """
        # Acquire semaphore slot to enforce global concurrency cap
        async with self.semaphore:
            start_time = time.perf_counter()
            try:
                # Enforce task-level cancellation and hard timeout
                response = await asyncio.wait_for(
                    client.get(url),
                    timeout=self.timeout_seconds,
                )
                latency = (time.perf_counter() - start_time) * 1000

                # Check if HTTP returned 4xx or 5xx
                if response.is_error:
                    return AsyncFetchResponse(
                        url=url,
                        status_code=response.status_code,
                        data=response.text,
                        latency_ms=latency,
                        error=f"HTTP {response.status_code} received: {response.reason_phrase}",
                        error_category=FetchErrorCategory.HTTP_STATUS,
                    )

                # Attempt JSON decoding with graceful fallback to raw text
                try:
                    data = response.json()
                except Exception:
                    data = response.text

                logger.debug("Successfully fetched %s (status=%d, latency=%.2f ms)", url, response.status_code, latency)
                return AsyncFetchResponse(
                    url=url,
                    status_code=response.status_code,
                    data=data,
                    latency_ms=latency,
                    error=None,
                    error_category=FetchErrorCategory.NONE,
                )

            except (asyncio.TimeoutError, httpx.TimeoutException) as exc:
                latency = (time.perf_counter() - start_time) * 1000
                logger.warning("Timeout fetching %s after %.2f ms: %s", url, latency, exc)
                return AsyncFetchResponse(
                    url=url,
                    status_code=0,
                    data=None,
                    latency_ms=latency,
                    error=f"Request timed out after {self.timeout_seconds}s",
                    error_category=FetchErrorCategory.TIMEOUT,
                )

            except asyncio.CancelledError:
                latency = (time.perf_counter() - start_time) * 1000
                logger.warning("Fetch cancelled for %s after %.2f ms", url, latency)
                return AsyncFetchResponse(
                    url=url,
                    status_code=0,
                    data=None,
                    latency_ms=latency,
                    error="Task was cancelled by event loop or caller",
                    error_category=FetchErrorCategory.CANCELLED,
                )

            except (httpx.ConnectError, httpx.NetworkError) as exc:
                latency = (time.perf_counter() - start_time) * 1000
                logger.warning("Connection failure fetching %s: %s", url, exc)
                return AsyncFetchResponse(
                    url=url,
                    status_code=0,
                    data=None,
                    latency_ms=latency,
                    error=f"Network connection error: {exc}",
                    error_category=FetchErrorCategory.CONNECTION,
                )

            except Exception as exc:
                latency = (time.perf_counter() - start_time) * 1000
                logger.exception("Unexpected error fetching %s: %s", url, exc)
                return AsyncFetchResponse(
                    url=url,
                    status_code=0,
                    data=None,
                    latency_ms=latency,
                    error=f"Unexpected error: {exc}",
                    error_category=FetchErrorCategory.UNKNOWN,
                )

    async def fetch_all(
        self,
        urls: list[str],
        client: httpx.AsyncClient | None = None,
    ) -> list[AsyncFetchResponse]:
        """Fetch all URLs concurrently using asyncio.gather with partial failure isolation.

        Args:
            urls: List of URL strings to query.
            client: Optional pre-configured httpx.AsyncClient (e.g. for testing).

        Returns:
            List of AsyncFetchResponse objects matching input order.
        """
        if not urls:
            return []

        async def _run_tasks(active_client: httpx.AsyncClient) -> list[AsyncFetchResponse]:
            tasks = [self.fetch_one(active_client, url) for url in urls]
            # return_exceptions=True prevents one crash from terminating sibling coroutines
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

            processed: list[AsyncFetchResponse] = []
            for url, res in zip(urls, raw_results):
                if isinstance(res, AsyncFetchResponse):
                    processed.append(res)
                elif isinstance(res, Exception):
                    processed.append(
                        AsyncFetchResponse(
                            url=url,
                            status_code=0,
                            data=None,
                            latency_ms=0.0,
                            error=f"Unhandled coroutine exception: {res}",
                            error_category=FetchErrorCategory.UNKNOWN,
                        )
                    )
                else:
                    processed.append(
                        AsyncFetchResponse(
                            url=url,
                            status_code=0,
                            data=None,
                            latency_ms=0.0,
                            error="Unknown result type returned",
                            error_category=FetchErrorCategory.UNKNOWN,
                        )
                    )
            return processed

        if client is not None:
            return await _run_tasks(client)

        async with httpx.AsyncClient(timeout=self.timeout) as new_client:
            return await _run_tasks(new_client)

    async def fetch_in_batches(
        self,
        urls: list[str],
        batch_size: int = 5,
        show_progress: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> list[AsyncFetchResponse]:
        """Process URLs in partitioned batches with optional Rich progress tracking.

        In AI data pipelines (e.g. indexing 1,000 documents or downloading bulk papers),
        running 1,000 tasks simultaneously—even with a semaphore—can exhaust socket descriptors
        or consume excessive memory. Partitioning into batches provides backpressure.

        Args:
            urls: Full list of URLs to process.
            batch_size: Number of URLs per batch chunk.
            show_progress: If True, renders a Rich progress bar in the terminal.
            client: Optional injected httpx.AsyncClient.

        Returns:
            Combined list of all AsyncFetchResponse objects.
        """
        if not urls:
            return []

        chunks = [urls[i : i + batch_size] for i in range(0, len(urls), batch_size)]
        all_results: list[AsyncFetchResponse] = []

        if show_progress:
            try:
                from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                ) as progress:
                    task_tracker = progress.add_task(
                        f"Fetching {len(urls)} URLs in {len(chunks)} batches...",
                        total=len(urls),
                    )
                    for batch_idx, chunk in enumerate(chunks, 1):
                        logger.info("Starting batch %d/%d (%d URLs)", batch_idx, len(chunks), len(chunk))
                        batch_results = await self.fetch_all(chunk, client=client)
                        all_results.extend(batch_results)
                        progress.update(task_tracker, advance=len(chunk))
                return all_results
            except ImportError:
                logger.info("Rich library not detected; falling back to standard batch logging.")

        # Standard execution without Rich UI
        for batch_idx, chunk in enumerate(chunks, 1):
            logger.info("Executing batch %d/%d (%d URLs)", batch_idx, len(chunks), len(chunk))
            batch_results = await self.fetch_all(chunk, client=client)
            all_results.extend(batch_results)

        return all_results


# ---------------------------------------------------------------------------
# CLI Benchmark Routine
# ---------------------------------------------------------------------------
async def benchmark(concurrency: int = 5, total_requests: int = 10) -> None:
    """Benchmark concurrent async operations against a sample REST service."""
    urls = [f"https://jsonplaceholder.typicode.com/posts/{i}" for i in range(1, total_requests + 1)]
    print(f"🚀 Benchmarking concurrent fetch across {len(urls)} URLs (concurrency={concurrency})...")

    fetcher = ConcurrentAsyncFetcher(max_concurrency=concurrency)
    start = time.perf_counter()
    responses = await fetcher.fetch_in_batches(urls, batch_size=5, show_progress=True)
    total_time = time.perf_counter() - start

    successful = [r for r in responses if r.is_success]
    failures = [r for r in responses if not r.is_success]
    avg_latency = sum(r.latency_ms for r in successful) / len(successful) if successful else 0

    print(f"\n✅ Completed in {total_time:.2f}s!")
    print(f"📊 Succeeded: {len(successful)}/{len(urls)} | Failed: {len(failures)}/{len(urls)}")
    print(f"⚡ Average successful latency: {avg_latency:.2f} ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="High-performance Concurrent Async Fetcher")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrency limit")
    parser.add_argument("--count", type=int, default=10, help="Number of URLs to fetch")
    args = parser.parse_args()

    asyncio.run(benchmark(concurrency=args.concurrency, total_requests=args.count))


if __name__ == "__main__":
    main()
