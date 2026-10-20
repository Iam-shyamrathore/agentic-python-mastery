"""Topic 06: Concurrent Async Fetcher (Complete Reference Solution).

Production-grade asyncio fetcher with Semaphore concurrency control,
connection pooling, performance metrics, and resilient error recovery.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import time
from typing import Any
import httpx


@dataclass
class AsyncFetchResponse:
    url: str
    status_code: int
    data: Any
    latency_ms: float
    error: str | None = None


class ConcurrentAsyncFetcher:
    """Fetches multiple URLs concurrently with concurrency bounds."""

    def __init__(self, max_concurrency: int = 5, timeout_seconds: float = 10.0) -> None:
        self.max_concurrency = max_concurrency
        self.timeout = httpx.Timeout(timeout_seconds)
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def fetch_one(self, client: httpx.AsyncClient, url: str) -> AsyncFetchResponse:
        """Fetch a single URL guarded by semaphore with timing."""
        async with self.semaphore:
            start_time = time.perf_counter()
            try:
                response = await client.get(url)
                latency = (time.perf_counter() - start_time) * 1000
                try:
                    data = response.json()
                except Exception:
                    data = response.text
                return AsyncFetchResponse(
                    url=url,
                    status_code=response.status_code,
                    data=data,
                    latency_ms=latency,
                )
            except Exception as exc:
                latency = (time.perf_counter() - start_time) * 1000
                return AsyncFetchResponse(
                    url=url,
                    status_code=0,
                    data=None,
                    latency_ms=latency,
                    error=str(exc),
                )

    async def fetch_all(self, urls: list[str]) -> list[AsyncFetchResponse]:
        """Fetch all URLs concurrently using asyncio.gather."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [self.fetch_one(client, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=False)
            return list(results)


async def benchmark() -> None:
    urls = [f"https://jsonplaceholder.typicode.com/posts/{i}" for i in range(1, 11)]
    print(f"🚀 Benchmarking concurrent fetch across {len(urls)} URLs...")

    fetcher = ConcurrentAsyncFetcher(max_concurrency=5)
    start = time.perf_counter()
    responses = await fetcher.fetch_all(urls)
    total_time = time.perf_counter() - start

    successful = [r for r in responses if r.status_code == 200]
    avg_latency = sum(r.latency_ms for r in successful) / len(successful) if successful else 0

    print(f"✅ Finished in {total_time:.2f}s! ({len(successful)}/{len(urls)} succeeded)")
    print(f"📊 Average per-request latency: {avg_latency:.2f} ms")


def main() -> None:
    asyncio.run(benchmark())


if __name__ == "__main__":
    main()
