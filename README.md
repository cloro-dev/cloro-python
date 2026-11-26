# cloro Python SDK

The official Python SDK for [**cloro**](https://cloro.dev), the API for AI answers.
It returns structured JSON from eight engines: ChatGPT, Google Search, Google News,
Google AI Overview, Google AI Mode, Gemini, Bing Search and Bing AI Mode (Copilot
Search in Bing). cloro also runs an [MCP server](https://cloro.dev/docs/integrations/mcp) that exposes
its monitor endpoints as tools for Claude, Codex, Cursor or your own agent.

cloro also has an official JS SDK,
[`@cloro-dev/cloro`](https://www.npmjs.com/package/@cloro-dev/cloro).

Use the SDK, or [just `curl` it](https://cloro.dev/docs): same clean response
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
Google Search, Google News and Bing Search take a `query`.

```python
client.monitor.chatgpt(prompt="...", country="US")
client.monitor.gemini(prompt="...", country="US")
client.monitor.aimode(prompt="...", country="US")           # Google AI Mode
client.monitor.bing_aimode(prompt="...", country="US")      # Bing AI Mode

client.monitor.google(query="best crm", country="US", pages=1)
client.monitor.google_news(query="acme corp", country="US")
client.monitor.bing(query="best crm", country="US")         # Bing Search
```

Pass `include={...}` to request extra formats: `markdown`, `html`,
`searchQueries`, `shopping`, and more, depending on the engine.

### Bing AI Mode

`bing_aimode()` gets the answer from Bing AI Mode. The
result has `text`, `sources` and `citationPills`. Set `include` to get
`markdown`, or `html` (a URL to the HTML of the page that Bing shows). Use
`state` to target a US state. `state` is valid only with `country="US"`.

```python
res = client.monitor.bing_aimode(
    prompt="best running shoes for flat feet",
    country="US",
    state="CA",
    include={"markdown": True, "html": True},
)

print(res["result"]["text"])
for pill in res["result"]["citationPills"]:
    print(pill["citationPillId"], pill["domain"], pill["url"])
```

The prompt can have a maximum of 3,500 characters after URL encoding. Non-Latin
scripts take more characters when encoded, so the limit for them is lower. A
request costs 4 credits, plus 2 credits for a sync request and 2 credits when
you set `state`. An async task (`BING_AIMODE`) does not have the 2-credit sync
charge. `client.countries(model="bing_aimode")` gives the supported countries.

### Bing Search

`bing()` gets the Bing results with the AI Overview. The result has
`organicResults`, `ads` when the page has ads and, when you request it and Bing
shows one, `aioverview`. They have the same shapes as in Google Search. Set `include` to get `html` (the
results page), or `aioverview`. Set `aioverview` to `True`, or to
`{"markdown": True}` to also get the AI Overview as markdown. `pages` (1 to 10, 2 credits for each
page after the first) and `first` (the result to start at, default 1) select the
results. Bing shows its AI summary only on the first page. Bing Search has no
`state` or `device`. The country selects the Bing market.

```python
res = client.monitor.bing(
    query="best running shoes for flat feet",
    country="US",
    include={"aioverview": {"markdown": True}},
)

for r in res["result"]["organicResults"]:
    print(r["position"], r["link"], r["title"])
if "aioverview" in res["result"]:
    print(res["result"]["aioverview"]["markdown"])
```

The query can have a maximum of 3,500 characters after URL encoding. Non-Latin
scripts take more characters when encoded, so the limit for them is lower. A
request costs 3 credits, plus 2 credits for a sync request and 2 credits when
you set `aioverview`. An async task (`BING`) does not have the 2-credit sync
charge. `client.countries(model="bing")` gives the supported countries.

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
    {"task_type": "GEMINI", "payload": {"prompt": "q2", "country": "GB"}},
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

Valid `task_type` values: `CHATGPT`, `GEMINI`, `AIMODE`, `BING_AIMODE`,
`GOOGLE`, `GOOGLE_NEWS`, `BING`.

## Configuration

```python
client = Cloro(
    api_key="sk_live_...",
    base_url="https://api.cloro.dev",  # override if needed
    timeout=300.0,                      # per-request seconds (the default)
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
client.countries(model="bing_aimode")
client.countries(model="bing")
client.states()                # US states for location-targeted Google
```

## Links

- [cloro.dev](https://cloro.dev): the hosted SERP + AI answer-engine API
- [SERP API](https://cloro.dev/serp-api/): the Google Search endpoint this SDK wraps
- [Python guide](https://cloro.dev/integrations/python/): quickstart, recipes, and production patterns
- [Docs](https://cloro.dev/docs) and [API reference (OpenAPI)](https://cloro.dev/docs/api-reference/openapi.json)
- [Pricing](https://cloro.dev/pricing/) · [Dashboard](https://dashboard.cloro.dev/)
- TypeScript SDK: [cloro-node](https://github.com/cloro-dev/cloro-node)

## License

MIT
