"""Tests for Topic 03: Resilient API Fetcher."""

import sys
from pathlib import Path
import httpx
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from api_fetcher import (
    APIClientError,
    FetchResult,
    RateLimitError,
    ResilientAPIClient,
    ServerUnavailableError,
)


def test_fetch_result_dataclass():
    res = FetchResult(status_code=200, data={"ok": True}, elapsed_ms=12.5)
    assert res.status_code == 200
    assert res.data["ok"] is True
    assert res.elapsed_ms == 12.5


def test_client_url_construction():
    client = ResilientAPIClient(base_url="https://api.example.com/v1")
    assert client._build_url("users") == "https://api.example.com/v1/users"
    assert client._build_url("/users") == "https://api.example.com/v1/users"
    assert client._build_url("https://other.com/ping") == "https://other.com/ping"
    client.close()


def test_client_backoff_calculation():
    client = ResilientAPIClient(backoff_base=0.1)
    d0 = client._calculate_backoff(0)
    d1 = client._calculate_backoff(1)
    assert d0 > 0.1
    assert d1 > d0
    client.close()
