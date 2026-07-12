# Contributing

## Layout

```
src/cloro/
  _client.py            # Cloro client: auth, HTTP, retries, error mapping
  _exceptions.py        # exception hierarchy (CloroError -> ...)
  resources/
    monitor.py          # POST /v1/monitor/* (sync per-engine methods)
    async_tasks.py      # /v1/async/* queue + the wait() poller
openapi.json            # vendored source of truth for the API surface
tests/                  # httpx.MockTransport-based unit tests (no network)
```

## Source of truth

`openapi.json` (the cloro OpenAPI 3.1 spec, also served at
<https://cloro.dev/docs/api-reference/openapi.json>) is the contract. When the
API changes, refresh the vendored copy and reconcile the resource methods and
types against it.

The resource/type layer is intentionally thin and could be generated from the
spec (Stainless / Speakeasy / Fern) if the surface grows. The one piece to keep
hand-written regardless is the async **poller** in `resources/async_tasks.py` —
generators produce request methods, not polling ergonomics.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

Tests must not hit the network — inject an `httpx.Client(transport=...)` via the
`http_client=` argument (see `tests/test_client.py`).

## Releasing

Bump `src/cloro/_version.py`, update `CHANGELOG.md`, tag `vX.Y.Z`, and publish a
GitHub Release. The `publish` workflow builds and uploads to PyPI on release.
