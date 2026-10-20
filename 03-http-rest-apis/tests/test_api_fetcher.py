"""Tests for Topic 03: Resilient API Fetcher."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import time
import httpx
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from api_fetcher import (
    APIClientError,
    CircuitBreakerOpenError,
    CircuitState,
    FetchResult,
    RateLimitError,
    ResilientAPIClient,
    ServerUnavailableError,
    parse_retry_after,
)


def test_fetch_result_dataclass():
    res = FetchResult(status_code=200, data={"ok": True}, elapsed_ms=12.5)
    assert res.status_code == 200
    assert res.data["ok"] is True
    assert res.elapsed_ms == 12.5
    assert res.headers == {}


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
    # If Retry-After is supplied, it overrides calculation
    assert client._calculate_backoff(0, retry_after=7.5) == 7.5
    client.close()


def test_parse_retry_after_seconds():
    assert parse_retry_after("5") == 5.0
    assert parse_retry_after("12.5") == 12.5
    assert parse_retry_after(None) is None
    assert parse_retry_after("invalid") is None


def test_parse_retry_after_http_date():
    # Future date
    future = datetime.now(timezone.utc) + timedelta(seconds=60)
    http_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
    delay = parse_retry_after(http_date)
    assert delay is not None
    assert 55.0 <= delay <= 65.0


def test_fetch_result_rate_limit_headers():
    res = FetchResult(
        status_code=200,
        data={},
        elapsed_ms=10.0,
        headers={"x-ratelimit-remaining": "49", "retry-after": "3"},
    )
    assert res.rate_limit_remaining == 49
    assert res.retry_after == 3.0


def test_client_connection_pooling_and_headers():
    client = ResilientAPIClient(
        max_connections=50,
        max_keepalive_connections=10,
        custom_headers={"X-Agent-ID": "agent_007"},
    )
    assert client.limits.max_connections == 50
    assert client.limits.max_keepalive_connections == 10
    assert "AgenticPythonMastery" in client.headers["User-Agent"]
    assert client.headers["X-Agent-ID"] == "agent_007"
    client.close()


def test_circuit_breaker_state_flow():
    client = ResilientAPIClient(
        failure_threshold=3,
        recovery_timeout=0.2,  # Short recovery timeout for fast test
    )
    assert client.circuit_state == CircuitState.CLOSED

    # Record 2 failures -> still CLOSED
    client._record_failure()
    client._record_failure()
    assert client.circuit_state == CircuitState.CLOSED

    # 3rd failure trips circuit to OPEN
    client._record_failure()
    assert client.circuit_state == CircuitState.OPEN

    # In OPEN state, requests should immediately raise CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        client._before_request_circuit_check()

    # Wait for recovery timeout
    time.sleep(0.25)

    # State transitions to HALF_OPEN to allow canary probe
    assert client.circuit_state == CircuitState.HALF_OPEN

    # Successful canary resets circuit to CLOSED
    client._record_success()
    assert client.circuit_state == CircuitState.CLOSED
    assert client._consecutive_failures == 0
    client.close()
