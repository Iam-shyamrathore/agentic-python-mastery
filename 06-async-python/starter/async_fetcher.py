"""Topic 06: Concurrent Async Fetcher (Starter Template).

Complete each TODO section alongside your AI Assistant.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
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
        """Fetch a single URL with error handling and timing."""
        # TODO: Guard with self.semaphore, record time, handle exceptions
        raise NotImplementedError("Implement fetch_one")

    async def fetch_all(self, urls: list[str]) -> list[AsyncFetchResponse]:
        """Fetch all URLs concurrently using asyncio.gather."""
        # TODO: Create an httpx.AsyncClient and gather fetch_one calls
        raise NotImplementedError("Implement fetch_all")


async def main() -> None:
    print("Welcome to Concurrent Async Fetcher! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    asyncio.run(main())
