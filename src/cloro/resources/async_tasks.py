"""Async task queue — enqueue work, then poll to completion.

This is where the SDK earns its keep over raw HTTP: :meth:`AsyncTasksResource.wait`
polls ``GET /v1/async/task/{id}`` with interval backoff and a timeout, and
:meth:`AsyncTasksResource.run` collapses create-then-wait into a single call.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .._exceptions import TaskFailedError, TaskTimeoutError

if TYPE_CHECKING:
    from .._client import Cloro

TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED"})

# Provider identifiers accepted by the ``taskType`` field.
TaskType = str

TaskRef = Union["AsyncTask", str]


@dataclass
class AsyncTask:
    """A handle to a queued task. Returned by :meth:`AsyncTasksResource.create`."""

    id: str
    status: str = "QUEUED"
    task_type: Optional[str] = None
    priority: Optional[int] = None
    created_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def _from_summary(cls, summary: Dict[str, Any]) -> "AsyncTask":
        return cls(
            id=summary["id"],
            status=summary.get("status", "QUEUED"),
            task_type=summary.get("taskType"),
            priority=summary.get("priority"),
            created_at=summary.get("createdAt"),
            raw=summary,
        )


def _task_id(task: TaskRef) -> str:
    return task.id if isinstance(task, AsyncTask) else task


def _to_request(task: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a task dict (snake_case or camelCase) into the API's shape."""
    out: Dict[str, Any] = {
        "taskType": task.get("task_type", task.get("taskType")),
        "payload": task.get("payload"),
    }
    for snake, camel in (
        ("priority", "priority"),
        ("idempotency_key", "idempotencyKey"),
        ("webhook", "webhook"),
    ):
        value = task.get(snake, task.get(camel))
        if value is not None:
            out[camel] = value
    return out


class AsyncTasksResource:
    """The ``/v1/async/*`` task queue."""

    def __init__(self, client: "Cloro") -> None:
        self._client = client

    # -- create ---------------------------------------------------------

    def create(
        self,
        task_type: TaskType,
        payload: Dict[str, Any],
        *,
        priority: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        webhook: Optional[Dict[str, Any]] = None,
    ) -> AsyncTask:
        """Enqueue a single task. ``POST /v1/async/task``.

        Args:
            task_type: One of ``CHATGPT``, ``GEMINI``, ``PERPLEXITY``, ``COPILOT``,
                ``GROK``, ``AIMODE``, ``GOOGLE``, ``GOOGLE_NEWS``.
            payload: Provider-specific body (e.g. ``{"prompt": ..., "country": ...}``,
                or ``{"query": ..., "country": ...}`` for Google Search).
            priority: 1-10, higher runs first (default 1).
            idempotency_key: Unique string to dedupe task creation.
            webhook: ``{"url": ...}`` to be notified on completion.
        """
        body = _to_request(
            {
                "task_type": task_type,
                "payload": payload,
                "priority": priority,
                "idempotency_key": idempotency_key,
                "webhook": webhook,
            }
        )
        resp = self._client.request("POST", "/v1/async/task", json=body)
        return AsyncTask._from_summary(resp["task"])

    def create_batch(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enqueue up to 500 tasks in one call. ``POST /v1/async/task/batch``.

        Each item is a dict with ``task_type`` and ``payload`` (plus optional
        ``priority`` / ``idempotency_key`` / ``webhook``). Returns the per-task
        ``results`` array, preserving input order. Successful items carry a
        ``task`` field; failed items carry an ``error`` field.
        """
        body = [_to_request(t) for t in tasks]
        resp = self._client.request("POST", "/v1/async/task/batch", json=body)
        return resp.get("results", [])

    # -- read -----------------------------------------------------------

    def retrieve(self, task: TaskRef) -> Dict[str, Any]:
        """Fetch a task's current status. ``GET /v1/async/task/{id}``.

        The ``response`` field is present only once the task is ``COMPLETED``
        or ``FAILED``.
        """
        return self._client.request("GET", f"/v1/async/task/{_task_id(task)}")

    def status(self) -> Dict[str, Any]:
        """Queue-wide status for your organization. ``GET /v1/async/status``."""
        return self._client.request("GET", "/v1/async/status")

    # -- poll -----------------------------------------------------------

    def wait(
        self,
        task: TaskRef,
        *,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
        backoff: float = 1.5,
        max_interval: float = 15.0,
    ) -> Dict[str, Any]:
        """Poll a task until it reaches a terminal status, then return it.

        Args:
            task: An :class:`AsyncTask` or a task id string.
            poll_interval: Seconds before the first poll; grows by ``backoff``.
            timeout: Give up after this many seconds (raises
                :class:`TaskTimeoutError`).
            backoff: Multiplier applied to the interval after each poll.
            max_interval: Ceiling for the polling interval.

        Returns:
            The full ``TaskStatusResponse`` dict, including ``response`` once
            ``COMPLETED``.

        Raises:
            TaskFailedError: the task reached ``FAILED``.
            TaskTimeoutError: the task did not finish within ``timeout``.
        """
        deadline = time.monotonic() + timeout
        interval = poll_interval
        while True:
            status = self.retrieve(task)
            state = status.get("task", {}).get("status")
            if state == "COMPLETED":
                return status
            if state == "FAILED":
                raise TaskFailedError(
                    f"Task {_task_id(task)} failed", task=task, response=status
                )

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TaskTimeoutError(
                    f"Task {_task_id(task)} did not complete within {timeout}s "
                    f"(last status: {state})",
                    task=task,
                )
            time.sleep(min(interval, remaining))
            interval = min(interval * backoff, max_interval)

    def run(
        self,
        task_type: TaskType,
        payload: Dict[str, Any],
        *,
        priority: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        webhook: Optional[Dict[str, Any]] = None,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
        backoff: float = 1.5,
        max_interval: float = 15.0,
    ) -> Dict[str, Any]:
        """Create a task and block until it completes. Convenience for
        :meth:`create` + :meth:`wait`."""
        task = self.create(
            task_type,
            payload,
            priority=priority,
            idempotency_key=idempotency_key,
            webhook=webhook,
        )
        return self.wait(
            task,
            poll_interval=poll_interval,
            timeout=timeout,
            backoff=backoff,
            max_interval=max_interval,
        )
