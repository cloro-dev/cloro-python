"""HTTP client for the cloro API."""
from __future__ import annotations

import os
import platform
import time
from typing import Any, Dict, Optional

import httpx

from ._exceptions import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    CloroError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from ._version import __version__
from .resources.async_tasks import AsyncTasksResource
from .resources.monitor import MonitorResource

DEFAULT_BASE_URL = "https://api.cloro.dev"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 2

_STATUS_MAP = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
}

# Status codes that are safe to retry with backoff.
_RETRY_STATUS = {429, 500, 502, 503, 504}


def _backoff(attempt: int) -> float:
    """Exponential backoff: 0.5s, 1s, 2s, ... capped at 8s."""
    return min(0.5 * (2 ** (attempt - 1)), 8.0)


def _parse_retry_after(response: httpx.Response) -> Optional[float]:
    value = response.headers.get("retry-after")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _make_status_error(response: httpx.Response) -> APIStatusError:
    try:
        body: Any = response.json()
    except Exception:
        body = None

    message: Optional[str] = None
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            message = err.get("message")
        elif isinstance(err, str):
            message = err
    message = message or (response.text or f"HTTP {response.status_code}")

    cls = _STATUS_MAP.get(response.status_code)
    if cls is None:
        cls = InternalServerError if response.status_code >= 500 else APIStatusError
    return cls(
        message,
        status_code=response.status_code,
        response=response,
        body=body,
    )


class Cloro:
    """Client for the cloro API.

    One API for Google Search and every AI answer engine (ChatGPT, Gemini,
    Perplexity, Copilot, Grok, AI Overview, AI Mode). Real-time, structured JSON.

    Args:
        api_key: Your cloro API key (``sk_live_...``). Falls back to the
            ``CLORO_API_KEY`` environment variable.
        base_url: Override the API base URL (default ``https://api.cloro.dev``).
        timeout: Per-request timeout in seconds.
        max_retries: Retries for timeouts, connection errors, and 429/5xx.
        http_client: Inject a preconfigured ``httpx.Client`` (proxies, custom
            transport, testing). If provided, ``timeout`` is ignored.

    Example:
        >>> from cloro import Cloro
        >>> client = Cloro(api_key="sk_live_...")
        >>> res = client.monitor.chatgpt(
        ...     prompt="What do you know about Acme Corp?",
        ...     country="US",
        ...     include={"markdown": True},
        ... )
        >>> res["result"]["text"]
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        api_key = api_key or os.environ.get("CLORO_API_KEY")
        if not api_key:
            raise CloroError(
                "No API key provided. Pass api_key=... or set the "
                "CLORO_API_KEY environment variable."
            )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)

        self.monitor = MonitorResource(self)
        self.async_tasks = AsyncTasksResource(self)

    # -- reference data -------------------------------------------------

    def countries(self, model: Optional[str] = None) -> Any:
        """List supported countries, optionally filtered by engine ``model``."""
        params = {"model": model} if model else None
        return self.request("GET", "/v1/countries", params=params)

    def states(self) -> Any:
        """List supported US states (for location-targeted Google requests)."""
        return self.request("GET", "/v1/states")

    # -- transport ------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"cloro-python/{__version__} (python {platform.python_version()})",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        attempt = 0
        while True:
            try:
                response = self._client.request(
                    method, url, json=json, params=params, headers=self._headers()
                )
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    attempt += 1
                    time.sleep(_backoff(attempt))
                    continue
                raise APITimeoutError(f"Request to {url} timed out") from exc
            except httpx.HTTPError as exc:
                if attempt < self.max_retries:
                    attempt += 1
                    time.sleep(_backoff(attempt))
                    continue
                raise APIConnectionError(str(exc)) from exc

            if response.status_code >= 400:
                if response.status_code in _RETRY_STATUS and attempt < self.max_retries:
                    attempt += 1
                    retry_after = _parse_retry_after(response)
                    time.sleep(retry_after if retry_after is not None else _backoff(attempt))
                    continue
                raise _make_status_error(response)

            if not response.content:
                return None
            return response.json()

    # -- lifecycle ------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client (only if the SDK created it)."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "Cloro":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()
