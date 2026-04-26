# Changelog

All notable changes to the Invoance Python SDK are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While the SDK is pre-1.0, breaking changes are only introduced in MINOR releases
(0.x → 0.x+1) and always documented here. Once 1.0.0 ships, the standard SemVer
contract applies.

---

## [Unreleased]

_Nothing yet._

---

## [0.1.0] — 2026-04-26

Initial public release.

### Added

- **Events** — `client.events.ingest()`, `get()`, `list()`, `verify()` for
  signing-and-anchoring arbitrary compliance events with hex-SHA-256 payload
  hashes.
- **Documents** — `client.documents.anchor()` (hash-only) and `anchor_file()`
  (hashes + uploads in one call), plus `get()`, `list()`, `verify()`, and
  `get_document_original()` for retrieving stored payloads.
- **AI attestations** — `client.attestations.ingest()`, `get()`, `list()`,
  `verify()`, `verify_signature()` for cryptographically attesting model
  inputs/outputs/decisions.
- **Traces** — full lifecycle: `create()`, `add_event()`, `seal()`,
  `get_proof()`, `export_proof_pdf()` for grouping items into sealed bundles
  with composite hashes.
- **`client.validate()`** — fast credential probe that never raises; returns
  `ValidationResult(valid, reason, base_url)`. Use in health checks and CI
  guards.
- **Typed error hierarchy** — `InvoanceError` base with `AuthenticationError`,
  `ForbiddenError`, `NotFoundError`, `ValidationError`, `ConflictError`,
  `QuotaExceededError`, `ServerError`, `NetworkError`, `TimeoutError`. Every
  raised exception inherits from `InvoanceError` so consumers can catch the
  base type.
- **Client-side validation** — `document_hash`, `payload_hash`, `content_hash`
  must be valid 64-char hex SHA-256 before a request leaves the client.
- **Env-var configuration** — `INVOANCE_API_KEY` (required) and
  `INVOANCE_BASE_URL` (default: `https://api.invoance.com`) auto-loaded by
  `InvoanceClient()`. Explicit constructor args or a `ClientConfig` override.
- **`ClientConfig.load(...)` factory** — explicit env-var resolution for
  callers that want to construct a `ClientConfig` programmatically with
  fallback to environment variables.
- **Async-first** — built on `httpx.AsyncClient`, used as
  `async with InvoanceClient() as client: ...`.
- **PEP 561 typed package** — `py.typed` marker shipped so `mypy` and
  `pyright` pick up the bundled type hints with no extra stub install.
- **Examples** — full working scripts under `examples/` for events,
  documents, attestations, and the full trace workflow.

### Notes

- Requires Python 3.9+.
- Runtime deps: `httpx>=0.27,<1`, `pydantic>=2.0,<3`, `PyNaCl>=1.5,<2`.

[Unreleased]: https://github.com/Invoance/invoance-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Invoance/invoance-python/releases/tag/v0.1.0
