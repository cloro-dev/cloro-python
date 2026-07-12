"""Unit tests — no network; all HTTP is served by httpx.MockTransport."""
from __future__ import annotations

import httpx
import pytest

import cloro
from cloro import (
    AuthenticationError,
    Cloro,
    CloroError,
    RateLimitError,
    TaskFailedError,
    TaskTimeoutError,
)


def make_client(handler, **kwargs):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    return Cloro(api_key="sk_test", http_client=http, **kwargs)


def test_requires_api_key(monkeypatch):
    monkeypatch.delenv("CLORO_API_KEY", raising=False)
    with pytest.raises(CloroError):
        Cloro()


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("CLORO_API_KEY", "sk_env")
    assert Cloro().api_key == "sk_env"


def test_monitor_chatgpt_request_and_response():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = httpx.Request(
            request.method, request.url, content=request.content
        ).content.decode()
        return httpx.Response(200, json={"success": True, "result": {"text": "hi"}})

    client = make_client(handler)
    res = client.monitor.chatgpt(prompt="hello", country="US", include={"markdown": True})

    assert res["result"]["text"] == "hi"
    assert seen["url"] == "https://api.cloro.dev/v1/monitor/chatgpt"
    assert seen["auth"] == "Bearer sk_test"
    assert '"prompt":"hello"' in seen["body"]
    assert '"markdown":true' in seen["body"]


def test_monitor_google_uses_query():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"success": True, "result": {}})

    client = make_client(handler)
    client.monitor.google(query="best crm", country="US", pages=2)
    assert seen["url"].endswith("/v1/monitor/google")


def test_none_values_are_dropped_from_body():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"success": True, "result": {}})

    client = make_client(handler)
    client.monitor.chatgpt(prompt="x", country="US")  # include omitted
    assert "include" not in seen["body"]


def test_status_error_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    client = make_client(handler)
    with pytest.raises(AuthenticationError) as exc:
        client.monitor.chatgpt(prompt="x", country="US")
    assert exc.value.status_code == 401
    assert "bad key" in str(exc.value)


def test_rate_limit_retries_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "0"}, json={"error": "slow down"})
        return httpx.Response(200, json={"success": True, "result": {"text": "ok"}})

    client = make_client(handler, max_retries=2)
    res = client.monitor.chatgpt(prompt="x", country="US")
    assert res["result"]["text"] == "ok"
    assert calls["n"] == 2


def test_rate_limit_exhausts_retries():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "0"}, json={"error": "slow down"})

    client = make_client(handler, max_retries=1)
    with pytest.raises(RateLimitError):
        client.monitor.chatgpt(prompt="x", country="US")


def test_async_create_returns_task():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": True,
                "task": {"id": "t-1", "taskType": "CHATGPT", "status": "QUEUED", "priority": 1,
                         "createdAt": "2026-04-09T15:00:00.000Z"},
                "credits": {"creditsToCharge": 5, "creditsCharged": None},
            },
        )

    client = make_client(handler)
    task = client.async_tasks.create(task_type="CHATGPT", payload={"prompt": "x", "country": "US"})
    assert isinstance(task, cloro.AsyncTask)
    assert task.id == "t-1"
    assert task.status == "QUEUED"


def test_async_wait_polls_until_completed():
    states = iter(["QUEUED", "PROCESSING", "COMPLETED"])

    def handler(request: httpx.Request) -> httpx.Response:
        state = next(states)
        body = {"task": {"id": "t-1", "status": state}, "credits": {"creditsToCharge": 5,
                "creditsCharged": 5 if state == "COMPLETED" else None}}
        if state == "COMPLETED":
            body["response"] = {"success": True, "result": {"text": "done"}}
        return httpx.Response(200, json=body)

    client = make_client(handler)
    result = client.async_tasks.wait("t-1", poll_interval=0.0, backoff=1.0)
    assert result["task"]["status"] == "COMPLETED"
    assert result["response"]["result"]["text"] == "done"


def test_async_wait_raises_on_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"task": {"id": "t-1", "status": "FAILED"},
                                          "credits": {"creditsToCharge": 5, "creditsCharged": 0}})

    client = make_client(handler)
    with pytest.raises(TaskFailedError):
        client.async_tasks.wait("t-1", poll_interval=0.0)


def test_async_wait_times_out():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "task": {"id": "t-1", "status": "QUEUED"},
            "credits": {"creditsToCharge": 5, "creditsCharged": None},
        })

    client = make_client(handler)
    with pytest.raises(TaskTimeoutError):
        client.async_tasks.wait("t-1", poll_interval=0.0, timeout=0.0)


def test_create_batch_returns_results():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "success": True,
            "summary": {"total": 2, "succeeded": 1, "failed": 1},
            "results": [
                {"success": True, "index": 0, "task": {"id": "t-1", "status": "QUEUED"},
                 "credits": {"creditsToCharge": 5, "creditsCharged": None}},
                {"success": False, "index": 1, "error": {"code": "VALIDATION_ERROR",
                 "message": "bad", "timestamp": "2026-04-09T15:00:00.000Z"}},
            ],
        })

    client = make_client(handler)
    results = client.async_tasks.create_batch([
        {"task_type": "CHATGPT", "payload": {"prompt": "a", "country": "US"}},
        {"task_type": "CHATGPT", "payload": {}},
    ])
    assert len(results) == 2
    assert results[0]["task"]["id"] == "t-1"
    assert results[1]["error"]["code"] == "VALIDATION_ERROR"
