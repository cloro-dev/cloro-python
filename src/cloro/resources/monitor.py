"""Synchronous monitor endpoints — one call per AI engine or Google Search."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .._client import Cloro


class MonitorResource:
    """Real-time ``POST /v1/monitor/*`` endpoints.

    Each method blocks until the engine responds and returns the parsed
    ``{"success": ..., "result": {...}}`` envelope. For high-volume or
    long-running work, prefer the async task queue (:attr:`Cloro.async_tasks`).
    """

    def __init__(self, client: "Cloro") -> None:
        self._client = client

    def _run(self, path: str, body: Dict[str, Any]) -> Any:
        payload = {k: v for k, v in body.items() if v is not None}
        return self._client.request("POST", path, json=payload)

    # -- AI answer engines (prompt-based) -------------------------------

    def chatgpt(
        self, prompt: str, country: str, *, include: Optional[Dict[str, bool]] = None, **extra: Any
    ) -> Any:
        """Monitor ChatGPT. ``POST /v1/monitor/chatgpt``."""
        return self._run(
            "/v1/monitor/chatgpt",
            {"prompt": prompt, "country": country, "include": include, **extra},
        )

    def gemini(
        self, prompt: str, country: str, *, include: Optional[Dict[str, bool]] = None, **extra: Any
    ) -> Any:
        """Monitor Google Gemini. ``POST /v1/monitor/gemini``."""
        return self._run(
            "/v1/monitor/gemini",
            {"prompt": prompt, "country": country, "include": include, **extra},
        )

    def perplexity(
        self, prompt: str, country: str, *, include: Optional[Dict[str, bool]] = None, **extra: Any
    ) -> Any:
        """Monitor Perplexity. ``POST /v1/monitor/perplexity``."""
        return self._run(
            "/v1/monitor/perplexity",
            {"prompt": prompt, "country": country, "include": include, **extra},
        )

    def copilot(
        self, prompt: str, country: str, *, include: Optional[Dict[str, bool]] = None, **extra: Any
    ) -> Any:
        """Monitor Microsoft Copilot. ``POST /v1/monitor/copilot``."""
        return self._run(
            "/v1/monitor/copilot",
            {"prompt": prompt, "country": country, "include": include, **extra},
        )

    def grok(
        self, prompt: str, country: str, *, include: Optional[Dict[str, bool]] = None, **extra: Any
    ) -> Any:
        """Monitor Grok. ``POST /v1/monitor/grok``."""
        return self._run(
            "/v1/monitor/grok",
            {"prompt": prompt, "country": country, "include": include, **extra},
        )

    def aimode(
        self, prompt: str, country: str, *, include: Optional[Dict[str, bool]] = None, **extra: Any
    ) -> Any:
        """Monitor Google AI Mode. ``POST /v1/monitor/aimode``."""
        return self._run(
            "/v1/monitor/aimode",
            {"prompt": prompt, "country": country, "include": include, **extra},
        )

    # -- Google Search (query-based) ------------------------------------

    def google(
        self,
        query: str,
        country: str,
        *,
        location: Optional[str] = None,
        uule: Optional[str] = None,
        device: Optional[str] = None,
        pages: Optional[int] = None,
        include: Optional[Dict[str, bool]] = None,
        **extra: Any,
    ) -> Any:
        """Monitor Google Search (SERP). ``POST /v1/monitor/google``."""
        return self._run(
            "/v1/monitor/google",
            {
                "query": query,
                "country": country,
                "location": location,
                "uule": uule,
                "device": device,
                "pages": pages,
                "include": include,
                **extra,
            },
        )

    def google_news(
        self, query: str, country: str, *, include: Optional[Dict[str, bool]] = None, **extra: Any
    ) -> Any:
        """Monitor Google News. ``POST /v1/monitor/google/news``."""
        return self._run(
            "/v1/monitor/google/news",
            {"query": query, "country": country, "include": include, **extra},
        )
