"""cloro — the official Python SDK.

One API for Google Search and every AI answer engine (ChatGPT, Gemini,
Perplexity, Copilot, Grok, AI Overview, AI Mode). Real-time, structured JSON.

    from cloro import Cloro

    client = Cloro(api_key="sk_live_...")
    res = client.monitor.chatgpt(prompt="What is cloro?", country="US")
    print(res["result"]["text"])
"""
from ._client import Cloro
from ._exceptions import (
    APIConnectionError,
    APIError,
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
    TaskError,
    TaskFailedError,
    TaskTimeoutError,
)
from ._version import __version__
from .resources import AsyncTask

__all__ = [
    "Cloro",
    "AsyncTask",
    "__version__",
    "CloroError",
    "APIError",
    "APIConnectionError",
    "APITimeoutError",
    "APIStatusError",
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "InternalServerError",
    "TaskError",
    "TaskFailedError",
    "TaskTimeoutError",
]
