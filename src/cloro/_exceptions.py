"""Exception hierarchy for the cloro SDK.

All errors derive from :class:`CloroError`, so a single ``except CloroError``
catches everything the SDK can raise. HTTP failures map to
:class:`APIStatusError` subclasses by status code; the async task poller raises
:class:`TaskFailedError` / :class:`TaskTimeoutError`.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

__all__ = [
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


class CloroError(Exception):
    """Base class for every error raised by the SDK."""


class APIError(CloroError):
    """Base class for errors originating from an HTTP request."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response: Any = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response
        self.body = body


class APIConnectionError(APIError):
    """The request could not reach the cloro API (DNS, TLS, socket errors)."""


class APITimeoutError(APIConnectionError):
    """The request timed out before a response was received."""


class APIStatusError(APIError):
    """The API returned a non-2xx status code."""


class BadRequestError(APIStatusError):
    """400 — the request was malformed or failed validation."""


class AuthenticationError(APIStatusError):
    """401 — the API key is missing or invalid."""


class PermissionDeniedError(APIStatusError):
    """403 — the API key is not allowed to perform this action."""


class NotFoundError(APIStatusError):
    """404 — the requested resource does not exist."""


class ConflictError(APIStatusError):
    """409 — the request conflicts with current state (e.g. a reused idempotency key)."""


class RateLimitError(APIStatusError):
    """429 — too many requests; retry after backing off."""


class InternalServerError(APIStatusError):
    """5xx — the API failed to process the request."""


class TaskError(CloroError):
    """Base class for async task queue errors."""


class TaskFailedError(TaskError):
    """An async task reached the ``FAILED`` terminal status while polling."""

    def __init__(
        self,
        message: str,
        *,
        task: Any = None,
        response: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.task = task
        self.response = response


class TaskTimeoutError(TaskError):
    """An async task did not reach a terminal status within the poll timeout."""

    def __init__(self, message: str, *, task: Any = None) -> None:
        super().__init__(message)
        self.task = task
