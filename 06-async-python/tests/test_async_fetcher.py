"""Tests for Topic 06: Async Python Concurrent Fetcher.

Validates concurrency boundaries, timeout and cancellation handling,
fine-grained error categorization, batching, and resilient partial failure recovery.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import httpx
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from async_fetcher import AsyncFetchResponse, ConcurrentAsyncFetcher, FetchErrorCategory


def test_async_fetch_response_dataclass():
    res = AsyncFetchResponse(url="http://test.com", status_code=200, data={"ok": True}, latency_ms=45.2)
    assert res.status_code == 200
    assert res.error is None
    assert res.latency_ms == 45.2
    assert res.is_success is True
    assert res.error_category == FetchErrorCategory.NONE


@pytest.mark.asyncio
async def test_semaphore_limiting():
    fetcher = ConcurrentAsyncFetcher(max_concurrency=2)
    assert fetcher.semaphore._value == 2


@pytest.mark.asyncio
async def test_fetch_one_success_mocked():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"title": "Test Title", "body": "Test Body"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        fetcher = ConcurrentAsyncFetcher(max_concurrency=2)
        res = await fetcher.fetch_one(client, "https://api.test/resource")

        assert res.is_success is True
        assert res.status_code == 200
        assert res.data["title"] == "Test Title"
        assert res.error is None
        assert res.error_category == FetchErrorCategory.NONE
        assert res.latency_ms >= 0


@pytest.mark.asyncio
async def test_fetch_one_http_status_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        fetcher = ConcurrentAsyncFetcher(max_concurrency=2)
        res = await fetcher.fetch_one(client, "https://api.test/fail")

        assert res.is_success is False
        assert res.status_code == 500
        assert res.error_category == FetchErrorCategory.HTTP_STATUS
        assert "HTTP 500" in res.error


@pytest.mark.asyncio
async def test_fetch_one_timeout_error_categorized():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Socket read timed out")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        fetcher = ConcurrentAsyncFetcher(max_concurrency=2, timeout_seconds=0.5)
        res = await fetcher.fetch_one(client, "https://api.test/timeout")

        assert res.is_success is False
        assert res.status_code == 0
        assert res.error_category == FetchErrorCategory.TIMEOUT
        assert "timed out" in res.error.lower()


@pytest.mark.asyncio
async def test_fetch_one_connection_error_categorized():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused by peer")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        fetcher = ConcurrentAsyncFetcher(max_concurrency=2)
        res = await fetcher.fetch_one(client, "https://api.test/unreachable")

        assert res.is_success is False
        assert res.status_code == 0
        assert res.error_category == FetchErrorCategory.CONNECTION
        assert "connection" in res.error.lower()


@pytest.mark.asyncio
async def test_fetch_one_cancellation_handled():
    async def slow_handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5.0)
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(slow_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        fetcher = ConcurrentAsyncFetcher(max_concurrency=2, timeout_seconds=10.0)
        task = asyncio.create_task(fetcher.fetch_one(client, "https://api.test/slow"))

        # Give task a moment to start and enter wait
        await asyncio.sleep(0.02)
        task.cancel()
        res = await task

        assert res.is_success is False
        assert res.error_category == FetchErrorCategory.CANCELLED
        assert res.status_code == 0
        assert "cancelled" in res.error.lower()


@pytest.mark.asyncio
async def test_fetch_all_partial_failures():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "timeout" in url:
            raise httpx.ReadTimeout("Timeout")
        if "error" in url:
            return httpx.Response(502, text="Bad Gateway")
        return httpx.Response(200, json={"url": url})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        fetcher = ConcurrentAsyncFetcher(max_concurrency=3, timeout_seconds=1.0)
        urls = [
            "https://api.test/item1",
            "https://api.test/timeout",
            "https://api.test/error",
            "https://api.test/item2",
        ]
        results = await fetcher.fetch_all(urls, client=client)

        assert len(results) == 4
        # Item 1 succeeded
        assert results[0].is_success is True
        assert results[0].status_code == 200

        # Item 2 timed out
        assert results[1].is_success is False
        assert results[1].error_category == FetchErrorCategory.TIMEOUT

        # Item 3 HTTP error
        assert results[2].is_success is False
        assert results[2].error_category == FetchErrorCategory.HTTP_STATUS
        assert results[2].status_code == 502

        # Item 4 succeeded
        assert results[3].is_success is True
        assert results[3].status_code == 200


@pytest.mark.asyncio
async def test_fetch_in_batches():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"url": str(request.url)})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        fetcher = ConcurrentAsyncFetcher(max_concurrency=2)
        urls = [f"https://api.test/post/{i}" for i in range(7)]

        # Fetch in batches of 3: chunks are [3, 3, 1]
        results = await fetcher.fetch_in_batches(urls, batch_size=3, show_progress=False, client=client)

        assert len(results) == 7
        for idx, res in enumerate(results):
            assert res.is_success is True
            assert res.url == urls[idx]
