"""Topic 03: Resilient API Fetcher (Complete Reference Solution).

Production-grade HTTP client with connection pooling, exponential backoff,
jitter, timeout enforcement, and typed response encapsulation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import random
import time
from typing import Any
import httpx


class APIClientError(Exception):
    """Base exception for API errors."""
    pass


class RateLimitError(APIClientError):
    """Raised when server returns 429 Too Many Requests."""
    pass


class ServerUnavailableError(APIClientError):
    """Raised when server returns 5xx errors."""
    pass


@dataclass
class FetchResult:
    status_code: int
    data: Any
    elapsed_ms: float


class ResilientAPIClient:
    """HTTP Client with connection pooling, timeouts, and retry logic."""

    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        base_url: str = "",
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._client = httpx.Client(timeout=self.timeout)

    def __enter__(self) -> "ResilientAPIClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        self._client.close()

    def _build_url(self, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        clean_endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{clean_endpoint}" if self.base_url else endpoint

    def _calculate_backoff(self, attempt: int) -> float:
        exponential = self.backoff_base * (2 ** attempt)
        jitter = random.uniform(0.05, 0.2)
        return min(10.0, exponential + jitter)

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> FetchResult:
        """Execute a GET request with automatic retry on 429 or 5xx."""
        url = self._build_url(endpoint)
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.perf_counter()
                response = self._client.get(url, params=params)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    if attempt < self.max_retries:
                        sleep_time = self._calculate_backoff(attempt)
                        time.sleep(sleep_time)
                        continue
                    if response.status_code == 429:
                        raise RateLimitError(f"Rate limited (429) after {self.max_retries} retries: {url}")
                    raise ServerUnavailableError(f"Server error ({response.status_code}) after retries: {url}")

                response.raise_for_status()

                try:
                    data = response.json()
                except Exception:
                    data = response.text

                return FetchResult(status_code=response.status_code, data=data, elapsed_ms=elapsed_ms)

            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    sleep_time = self._calculate_backoff(attempt)
                    time.sleep(sleep_time)
                    continue
                raise APIClientError(f"Connection failed after {self.max_retries} retries: {exc}") from exc

        raise APIClientError(f"Request failed: {last_exception}")

    def post(self, endpoint: str, json_data: dict[str, Any] | None = None) -> FetchResult:
        """Execute a POST request."""
        url = self._build_url(endpoint)
        start_time = time.perf_counter()
        response = self._client.post(url, json=json_data)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            data = response.text
        return FetchResult(status_code=response.status_code, data=data, elapsed_ms=elapsed_ms)


def main() -> None:
    parser = argparse.ArgumentParser(description="Resilient API Fetcher for AI Engineers")
    parser.add_argument("--url", default="https://jsonplaceholder.typicode.com/posts/1", help="URL to fetch")
    args = parser.parse_args()

    print(f"📡 Fetching data from: {args.url}")
    with ResilientAPIClient() as client:
        result = client.get(args.url)
        print(f"Status: {result.status_code} (took {result.elapsed_ms:.2f} ms)")
        print(f"Payload:\n{result.data}")


if __name__ == "__main__":
    main()
