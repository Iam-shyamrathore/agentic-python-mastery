"""Topic 03: Resilient API Fetcher (Starter Template).

Complete each TODO section alongside your AI Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import httpx


class APIClientError(Exception):
    """Base exception for API errors."""
    pass


class RateLimitError(APIClientError):
    """Raised when server returns 429 Too Many Requests."""
    pass


@dataclass
class FetchResult:
    status_code: int
    data: Any
    elapsed_ms: float


class ResilientAPIClient:
    """HTTP Client with connection pooling, timeouts, and retry logic."""

    def __init__(self, base_url: str = "", timeout_seconds: float = 10.0, max_retries: int = 3) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)
        self.max_retries = max_retries
        self._client = httpx.Client(timeout=self.timeout)

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        self._client.close()

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> FetchResult:
        """Execute a GET request with automatic retry on 429 or 5xx."""
        # TODO: Implement request execution with exponential backoff on retryable status codes
        raise NotImplementedError("Implement resilient get")

    def post(self, endpoint: str, json_data: dict[str, Any] | None = None) -> FetchResult:
        """Execute a POST request."""
        # TODO: Implement POST request execution
        raise NotImplementedError("Implement post")


def main() -> None:
    print("Welcome to Resilient API Fetcher! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
