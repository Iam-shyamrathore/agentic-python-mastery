"""Tests for Topic 06: Async Python Concurrent Fetcher."""

import sys
from pathlib import Path
import pytest
import pytest_asyncio

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from async_fetcher import AsyncFetchResponse, ConcurrentAsyncFetcher


def test_async_fetch_response_dataclass():
    res = AsyncFetchResponse(url="http://test.com", status_code=200, data={"ok": True}, latency_ms=45.2)
    assert res.status_code == 200
    assert res.error is None
    assert res.latency_ms == 45.2


@pytest.mark.asyncio
async def test_semaphore_limiting():
    fetcher = ConcurrentAsyncFetcher(max_concurrency=2)
    assert fetcher.semaphore._value == 2
