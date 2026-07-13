# cloro Python SDK

The official Python client for [**cloro**](https://cloro.dev) — one API for
Google Search and every AI answer engine (ChatGPT, Gemini, Perplexity, Copilot,
Grok, AI Overview, AI Mode). Real-time, structured JSON.

Use the SDK, or [just `curl` it](https://cloro.dev/docs) — same clean response
either way. The SDK adds typed methods, sensible retries, and a polling helper
for the async task queue so you don't hand-roll it.

## Installation

```bash
pip install cloro
```

Requires Python 3.8+.

## Quickstart

```python
from cloro import Cloro

client = Cloro(api_key="sk_live_...")  # or set CLORO_API_KEY

res = client.monitor.chatgpt(
    prompt="What do you know about Acme Corp?",
    country="US",
    include={"markdown": True},
)

print(res["result"]["text"])
for source in res["result"]["sources"]:
    print(source["position"], source["url"], source["label"])
```

The API key is read from the `CLORO_API_KEY` environment variable when you don't
pass `api_key=`. Get a key (and 500 free credits) at
[dashboard.cloro.dev](https://dashboard.cloro.dev/).

## Engines

Every engine is a method on `client.monitor`. AI engines take a `prompt`;
Google Search and Google News take a `query`.

```python
client.monitor.chatgpt(prompt="...", country="US")
client.monitor.gemini(prompt="...", country="US")
client.monitor.perplexity(prompt="...", country="US")
client.monitor.copilot(prompt="...", country="US")
client.monitor.grok(prompt="...", country="US")
client.monitor.aimode(prompt="...", country="US")           # Google AI Mode

client.monitor.google(query="best crm", country="US", pages=1)
client.monitor.google_news(query="acme corp", country="US")
```

Pass `include={...}` to request extra formats — `markdown`, `html`,
`searchQueries`, `shopping`, and more, depending on the engine.

## Async task queue

For high-volume or long-running work, enqueue tasks and poll them to completion.
`run()` does create-then-wait in one call:

```python
result = client.async_tasks.run(
    task_type="CHATGPT",
    payload={"prompt": "What is cloro?", "country": "US"},
)
print(result["response"])       # present once COMPLETED
print(result["credits"])        # credits reserved / charged
```

Prefer to manage the lifecycle yourself:

```python
task = client.async_tasks.create(
    task_type="GOOGLE",
    payload={"query": "serp api", "country": "US"},
    priority=5,
)
status = client.async_tasks.retrieve(task)   # non-blocking snapshot
result = client.async_tasks.wait(task, timeout=120, poll_interval=2)
```

Batch up to 500 tasks in a single request (results preserve input order):

```python
results = client.async_tasks.create_batch([
    {"task_type": "CHATGPT", "payload": {"prompt": "q1", "country": "US"}},
    {"task_type": "PERPLEXITY", "payload": {"prompt": "q2", "country": "GB"}},
])
for item in results:
    if item["success"]:
        client.async_tasks.wait(item["task"]["id"])
    else:
        print("failed:", item["error"]["message"])
```

Queue-wide status:

```python
client.async_tasks.status()   # queued / processing counts, concurrency usage
```

Valid `task_type` values: `CHATGPT`, `GEMINI`, `PERPLEXITY`, `COPILOT`, `GROK`,
`AIMODE`, `GOOGLE`, `GOOGLE_NEWS`.

## Configuration

```python
client = Cloro(
    api_key="sk_live_...",
    base_url="https://api.cloro.dev",  # override if needed
    timeout=60.0,                       # per-request seconds
    max_retries=2,                      # timeouts, connection errors, 429/5xx
)
```

The client is a context manager and pools connections:

```python
with Cloro() as client:
    client.monitor.chatgpt(prompt="...", country="US")
```

## Error handling

All errors subclass `CloroError`. HTTP failures map to status-specific types:

```python
from cloro import Cloro, AuthenticationError, RateLimitError, CloroError

try:
    client.monitor.chatgpt(prompt="...", country="US")
except AuthenticationError:
    ...  # 401 — bad or missing API key
except RateLimitError as e:
    ...  # 429 — back off and retry
except CloroError as e:
    ...  # everything else
```

`BadRequestError` (400), `PermissionDeniedError` (403), `NotFoundError` (404),
`ConflictError` (409), and `InternalServerError` (5xx) are also available, along
with `TaskFailedError` / `TaskTimeoutError` from the poller and
`APITimeoutError` / `APIConnectionError` from the transport.

## Reference data

```python
client.countries()             # supported countries
client.countries(model="chatgpt")
client.states()                # US states for location-targeted Google
```

## Links

- [cloro.dev](https://cloro.dev) — the hosted SERP + AI answer-engine API
- [SERP API](https://cloro.dev/serp-api/) — the Google Search endpoint this SDK wraps
- [Python guide](https://cloro.dev/integrations/python/) — quickstart, recipes, and production patterns
- [Docs](https://cloro.dev/docs) and [API reference (OpenAPI)](https://cloro.dev/docs/api-reference/openapi.json)
- [Pricing](https://cloro.dev/pricing/) · [Dashboard](https://dashboard.cloro.dev/)
- TypeScript SDK: [cloro-node](https://github.com/cloro-dev/cloro-node)

## License

MIT
