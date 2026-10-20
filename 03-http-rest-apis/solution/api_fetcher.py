"""Topic 03: Resilient API Fetcher (Complete Reference Solution).

Production-grade HTTP client with connection pooling, HTTP/2 support,
User-Agent branding, rate limit header extraction, RFC 7231 Retry-After handling,
exponential backoff with jitter, and a circuit breaker pattern.

Why this architecture is critical in AI Engineering:
---------------------------------------------------
1. Token & Request Rate Limiting (TPM & RPM):
   AI model providers (OpenAI, Anthropic, Gemini, Groq) enforce strict quotas:
   - Requests Per Minute (RPM)
   - Tokens Per Minute (TPM)
   When an agent pipeline runs concurrent evaluations or multi-agent swarms, requests
   frequently trigger 429 Too Many Requests. Naive clients immediately retry, creating
   a "thundering herd" that worsens the rate limit. Parsing the `Retry-After` header
   (seconds or RFC 7231 HTTP-date) allows agents to sleep exactly as requested.

2. Connection Pooling (TCP & TLS Handshake Overhead):
   Establishing a new TLS 1.3 handshake for every LLM call adds 50-150ms of latency per
   tool invocation. Using `httpx.Limits` maintains a warm keepalive connection pool,
   reusing active TCP sessions across thousands of sequential agent steps.

3. The Circuit Breaker Pattern:
   When an external tool, vector store, or LLM provider suffers an outage (continuous 500/503),
   blind retries waste compute, increase cloud bills, and cause cascading backpressure across
   upstream agent orchestrators. The circuit breaker detects consecutive failures, trips to
   an OPEN state to fail fast for a cooldown period, and tests recovery using a canary probe
   in HALF-OPEN state before restoring traffic.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from enum import Enum
import logging
import random
import sys
import time
from typing import Any
import httpx

# Configure structured standard logging
logger = logging.getLogger("api_fetcher")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

DEFAULT_USER_AGENT = "AgenticPythonMastery/1.0 (AI Agent HTTP Client)"


class CircuitState(str, Enum):
    """Lifecycle states for the Circuit Breaker pattern."""
    CLOSED = "closed"        # Normal operations: requests flow to network
    OPEN = "open"            # Outage detected: requests fail fast immediately
    HALF_OPEN = "half_open"  # Recovery testing: canary probe permitted


class APIClientError(Exception):
    """Base exception for API errors."""
    pass


class RateLimitError(APIClientError):
    """Raised when server returns 429 Too Many Requests."""
    pass


class ServerUnavailableError(APIClientError):
    """Raised when server returns 5xx errors."""
    pass


class CircuitBreakerOpenError(APIClientError):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""
    pass


def parse_retry_after(header_value: str | None) -> float | None:
    """Parse RFC 7231 / RFC 9110 Retry-After header.

    Supports:
    1. Integer/Float seconds representation (e.g. '5' or '120').
    2. HTTP-date representation (e.g. 'Wed, 21 Oct 2026 12:00:00 GMT').

    Args:
        header_value: Raw string header from response.

    Returns:
        Delay in seconds as a float, or None if missing or unparseable.
    """
    if not header_value:
        return None
    cleaned = header_value.strip()

    # 1. Try parsing as numeric seconds
    try:
        val = float(cleaned)
        return max(0.0, val)
    except ValueError:
        pass

    # 2. Try parsing as HTTP-date (RFC 1123 / RFC 7231)
    try:
        target_dt = parsedate_to_datetime(cleaned)
        now_dt = datetime.now(timezone.utc)
        diff_seconds = (target_dt - now_dt).total_seconds()
        return max(0.0, diff_seconds)
    except Exception:
        logger.debug("Failed to parse Retry-After header: '%s'", header_value)
        return None


@dataclass
class FetchResult:
    """Encapsulates HTTP response data, timing, and rate-limit metadata."""
    status_code: int
    data: Any
    elapsed_ms: float
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def rate_limit_remaining(self) -> int | None:
        """Extract remaining rate limit quota from common provider headers.
        
        Checks:
        - `x-ratelimit-remaining`
        - `ratelimit-remaining`
        - `x-ratelimit-remaining-requests`
        - `anthropic-ratelimit-tokens-remaining`
        """
        for candidate in (
            "x-ratelimit-remaining",
            "ratelimit-remaining",
            "x-ratelimit-remaining-requests",
            "anthropic-ratelimit-tokens-remaining",
        ):
            val = self.headers.get(candidate) or self.headers.get(candidate.lower())
            if val is not None:
                try:
                    return int(val)
                except ValueError:
                    pass
        return None

    @property
    def retry_after(self) -> float | None:
        """Extract and parse delay from Retry-After header if present."""
        raw = self.headers.get("retry-after") or self.headers.get("Retry-After")
        return parse_retry_after(raw)


class ResilientAPIClient:
    """Production-grade HTTP Client with connection pooling, retries, and circuit breaker."""

    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        base_url: str = "",
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 30.0,
        http2: bool = False,
        custom_headers: dict[str, str] | None = None,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        """Initialize the resilient client.

        Args:
            base_url: Optional root URL prefix for requests.
            timeout_seconds: Timeout for connect, read, and write operations.
            max_retries: Maximum retry attempts for transient errors.
            backoff_base: Multiplier for exponential backoff calculations.
            max_connections: Maximum simultaneous TCP connections in pool.
            max_keepalive_connections: Number of idle keepalive connections retained.
            keepalive_expiry: Time in seconds before idle keepalive connections expire.
            http2: Flag to request HTTP/2 multiplexing (falls back to HTTP/1.1 if h2 missing).
            custom_headers: Additional default headers to send with each request.
            failure_threshold: Consecutive failures needed to trip circuit to OPEN.
            recovery_timeout: Seconds to remain OPEN before attempting HALF_OPEN canary.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)
        self.max_retries = max_retries
        self.backoff_base = backoff_base

        # Configure connection pooling limits
        self.limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
        )

        # Merge headers with default User-Agent
        self.headers = {"User-Agent": DEFAULT_USER_AGENT}
        if custom_headers:
            self.headers.update(custom_headers)

        # Circuit breaker settings
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._circuit_state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time: float = 0.0

        # Construct underlying httpx.Client with defensive HTTP/2 check
        client_kwargs: dict[str, Any] = {
            "timeout": self.timeout,
            "limits": self.limits,
            "headers": self.headers,
        }
        if http2:
            try:
                import h2  # noqa: F401
                client_kwargs["http2"] = True
            except ImportError:
                logger.warning("HTTP/2 requested but 'h2' is not installed. Falling back to HTTP/1.1.")
                client_kwargs["http2"] = False

        self._client = httpx.Client(**client_kwargs)

    @property
    def circuit_state(self) -> CircuitState:
        """Current state of the circuit breaker."""
        if self._circuit_state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed to allow canary probe
            if (time.monotonic() - self._last_failure_time) >= self.recovery_timeout:
                self._circuit_state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entered HALF_OPEN state (probing canary request).")
        return self._circuit_state

    def _before_request_circuit_check(self) -> None:
        """Enforce circuit breaker rules before dispatching network request."""
        state = self.circuit_state
        if state == CircuitState.OPEN:
            remaining = self.recovery_timeout - (time.monotonic() - self._last_failure_time)
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN. Fast-failing request (retry in {remaining:.1f}s)."
            )

    def _record_success(self) -> None:
        """Update circuit breaker state upon a successful request."""
        if self._circuit_state == CircuitState.HALF_OPEN:
            logger.info("Canary probe succeeded. Resetting circuit breaker to CLOSED.")
        self._circuit_state = CircuitState.CLOSED
        self._consecutive_failures = 0

    def _record_failure(self) -> None:
        """Update circuit breaker state upon request failure."""
        self._consecutive_failures += 1
        self._last_failure_time = time.monotonic()
        if self._consecutive_failures >= self.failure_threshold:
            self._circuit_state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker tripped to OPEN after %d consecutive failures.",
                self._consecutive_failures,
            )

    def __enter__(self) -> "ResilientAPIClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        self._client.close()

    def _build_url(self, endpoint: str) -> str:
        """Normalize URL using configured base_url."""
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        clean_endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{clean_endpoint}" if self.base_url else endpoint

    def _calculate_backoff(self, attempt: int, retry_after: float | None = None) -> float:
        """Calculate wait delay with exponential backoff, jitter, or Retry-After header."""
        if retry_after is not None and retry_after > 0:
            return retry_after
        exponential = self.backoff_base * (2 ** attempt)
        jitter = random.uniform(0.05, 0.2)
        return min(10.0, exponential + jitter)

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> FetchResult:
        """Execute a GET request with connection pooling, retries, and circuit breaker.

        Args:
            endpoint: Relative path or full URL.
            params: Optional query parameters dictionary.

        Returns:
            `FetchResult` containing status, payload, elapsed time, and response headers.

        Raises:
            CircuitBreakerOpenError: If circuit breaker is currently OPEN.
            RateLimitError: If server responds with 429 after all retries exhausted.
            ServerUnavailableError: If server returns 5xx error after all retries.
            APIClientError: On network connectivity or unrecoverable HTTP error.
        """
        self._before_request_circuit_check()
        url = self._build_url(endpoint)
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.perf_counter()
                response = self._client.get(url, params=params)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                # Extract response headers as a case-insensitive or string dict
                headers_dict = dict(response.headers)

                # Check for retryable conditions (429 or 5xx)
                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    retry_delay = parse_retry_after(response.headers.get("retry-after"))
                    if attempt < self.max_retries:
                        sleep_time = self._calculate_backoff(attempt, retry_after=retry_delay)
                        logger.warning(
                            "Transient error (%d) fetching %s. Retrying in %.2fs (attempt %d/%d)...",
                            response.status_code,
                            url,
                            sleep_time,
                            attempt + 1,
                            self.max_retries,
                        )
                        time.sleep(sleep_time)
                        continue

                    self._record_failure()
                    if response.status_code == 429:
                        raise RateLimitError(f"Rate limited (429) after {self.max_retries} retries: {url}")
                    raise ServerUnavailableError(f"Server error ({response.status_code}) after retries: {url}")

                response.raise_for_status()
                self._record_success()

                try:
                    data = response.json()
                except Exception:
                    data = response.text

                return FetchResult(
                    status_code=response.status_code,
                    data=data,
                    elapsed_ms=elapsed_ms,
                    headers=headers_dict,
                )

            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    sleep_time = self._calculate_backoff(attempt)
                    logger.warning("Connection failure (%s). Retrying in %.2fs...", exc, sleep_time)
                    time.sleep(sleep_time)
                    continue
                self._record_failure()
                raise APIClientError(f"Connection failed after {self.max_retries} retries: {exc}") from exc

        self._record_failure()
        raise APIClientError(f"Request failed: {last_exception}")

    def post(self, endpoint: str, json_data: dict[str, Any] | None = None) -> FetchResult:
        """Execute a POST request with headers and circuit breaker."""
        self._before_request_circuit_check()
        url = self._build_url(endpoint)
        start_time = time.perf_counter()
        try:
            response = self._client.post(url, json=json_data)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            response.raise_for_status()
            self._record_success()
            try:
                data = response.json()
            except Exception:
                data = response.text
            return FetchResult(
                status_code=response.status_code,
                data=data,
                elapsed_ms=elapsed_ms,
                headers=dict(response.headers),
            )
        except Exception as exc:
            self._record_failure()
            raise APIClientError(f"POST request to {url} failed: {exc}") from exc


def main() -> None:
    """CLI entrypoint for demonstrating resilient API fetcher."""
    parser = argparse.ArgumentParser(description="Resilient API Fetcher for AI Engineers")
    parser.add_argument("--url", default="https://jsonplaceholder.typicode.com/posts/1", help="URL to fetch")
    args = parser.parse_args()

    print(f"📡 Fetching data from: {args.url}")
    with ResilientAPIClient() as client:
        result = client.get(args.url)
        print(f"Status: {result.status_code} (took {result.elapsed_ms:.2f} ms)")
        if result.rate_limit_remaining is not None:
            print(f"Rate Limit Remaining: {result.rate_limit_remaining}")
        print(f"Payload:\n{result.data}")


if __name__ == "__main__":
    main()
