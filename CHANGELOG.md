# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0]

### Removed

- `client.monitor.grok()` and the `GROK` task type. This is a breaking change.
  grok.com now shows a sign-up wall to all logged-out visitors before the first
  answer. cloro uses logged-out sessions, so it cannot get Grok answers. The
  API now rejects `/v1/monitor/grok` with a `400` (`MODEL_UNAVAILABLE`).

## [0.1.2]

### Changed

- The default request timeout is 300 seconds, up from 60. A sync request can
  run for several minutes, and the client retries on timeout.
- Corrected the `ConflictError` docstring: a 409 is a reused idempotency key.

## [0.1.1]

### Changed

- README and project URLs: link cloro.dev product pages (SERP API, Python
  guide, pricing) so the PyPI page references them.

## [0.1.0]

### Added

- Initial `Cloro` client with bearer-token auth, connection pooling, configurable
  timeout, and automatic retries on timeouts, connection errors, and 429/5xx.
- `client.monitor.*` — synchronous endpoints for ChatGPT, Gemini, Perplexity,
  Copilot, Grok, AI Mode, Google Search, and Google News.
- `client.async_tasks.*` — enqueue single/batch tasks, retrieve status, queue
  status, and a `wait()` poller with interval backoff plus a `run()` convenience
  (create + wait).
- `client.countries()` / `client.states()` reference-data helpers.
- Typed exception hierarchy rooted at `CloroError`.
