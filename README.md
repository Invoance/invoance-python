# Invoance Python SDK

Official Python SDK for the [Invoance](https://invoance.com) compliance API — cryptographic proof, document anchoring, AI attestation, traces, and audit logs.

- **Async** — every request method is a coroutine; use `async with InvoanceClient() as client:` and `await` each call.
- **Typed responses** — most methods return Pydantic models with typed attributes (`event.event_id`); the audit surface returns plain `dict`s.
- **Offline verification** — check Ed25519 signatures and recompute audit-log canonical hashes without trusting the server.

## Install

```bash
pip install invoance
```

Requires Python 3.9+.

## Quick start

Set your API key:

```bash
export INVOANCE_API_KEY=invoance_live_...
```

```python
import asyncio
import hashlib
from invoance import InvoanceClient

async def main():
    async with InvoanceClient() as client:

        # Ingest a compliance event
        event = await client.events.ingest(
            event_type="policy.approval",
            payload={"policy_id": "pol_001", "decision": "approved"},
        )
        print(event.event_id)

        # Anchor a document by hash
        doc_bytes = b"...your document bytes..."
        doc = await client.documents.anchor(
            document_hash=hashlib.sha256(doc_bytes).hexdigest(),
            document_ref="Invoice #1042",
        )
        print(doc.event_id)

        # Or use the file helper (hashes + uploads in one call)
        doc = await client.documents.anchor_file(
            file="./invoice.pdf",
            document_ref="Invoice #1042",
        )

        # Ingest an AI attestation
        att = await client.attestations.ingest(
            attestation_type="output",
            input="Summarize this contract",
            output="The contract states...",
            model_provider="openai",
            model_name="gpt-4o",
            model_version="2025-01-01",
            subject={"user_id": "u_42", "session_id": "sess_4f9a"},
        )
        print(att.attestation_id)

asyncio.run(main())
```

## Quick validation

Sanity-check that your API key works before wiring the SDK into a larger app:

```python
async with InvoanceClient() as client:
    result = await client.validate()
    if not result.valid:
        raise RuntimeError(f"Invoance: {result.reason} (base: {result.base_url})")
```

`validate()` probes `GET /v1/events?limit=1`, never raises, and returns a `ValidationResult(valid, reason, base_url)` — use it in health checks, startup scripts, or CI guards.

One-liner for a terminal sanity check, no SDK install required:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $INVOANCE_API_KEY" \
  "${INVOANCE_BASE_URL:-https://api.invoance.com}/v1/events?limit=1"
# 200 = key valid · 401 = bad key · anything else = investigate
```

## Configuration

The client reads from environment variables automatically:

| Variable | Required | Default |
|---|---|---|
| `INVOANCE_API_KEY` | Yes | — |
| `INVOANCE_BASE_URL` | No | `https://api.invoance.com` |

You can also pass them explicitly:

```python
client = InvoanceClient(
    api_key="invoance_live_...",
    timeout=60.0,
)
```

`api_key`, `base_url`, and `timeout` are mutually exclusive with the `config=` argument — pass either individual overrides or a full `ClientConfig`, not both.

For env-var fallback when constructing a config manually, use the factory:

```python
from invoance import ClientConfig

config = ClientConfig.load(timeout=60.0)  # reads INVOANCE_API_KEY / INVOANCE_BASE_URL from env
client = InvoanceClient(config=config)
```

## Resources

All resource methods are coroutines — `await` each one inside an `async with InvoanceClient() as client:` block. Keyword arguments are `snake_case`. Except where noted, responses are Pydantic models; read fields as attributes (`event.event_id`, `result.match_result`). The audit sub-resources are the exception — they return plain `dict`s.

### Events

```python
# POST /events — anchor a compliance event.
event = await client.events.ingest(
    event_type="user.login",
    payload={"user_id": "u_42"},
    event_time=None,        # optional ISO-8601; defaults to server now()
    trace_id=None,          # optional: attach to a trace
    idempotency_key=None,   # optional: safe-retry header
)
print(event.event_id, event.ingested_at)

# GET /events — paginated listing (max 500/page).
page = await client.events.list(
    page=1,
    limit=50,
    date_from=None,
    date_to=None,
    event_type=None,
)
for item in page.events:
    print(item.event_id, item.event_type)
print(page.total, page.has_more)

# GET /events/:event_id — fetch one event.
full = await client.events.get(event.event_id)
print(full.payload_hash, full.event_hash)

# POST /events/:event_id/verify — provide EXACTLY ONE of payload_hash / payload.
result = await client.events.verify(event.event_id, payload={"user_id": "u_42"})
# or: await client.events.verify(event.event_id, payload_hash="<64-hex sha256>")
print(result.match_result, result.matched_field, result.anchored_hash)
```

Passing neither `payload_hash` nor `payload` to `verify()` raises `ValidationError`.

### Documents

```python
# POST /document/anchor — anchor a document hash.
doc = await client.documents.anchor(
    document_hash="<64-hex sha256>",
    document_ref="Invoice #1042",
    event_type="invoice",           # optional classification
    original_bytes_b64=None,        # optional: base64 of the original, stored encrypted
    metadata={"amount": "1042.00"}, # optional JSON metadata
    trace_id=None,
    idempotency_key=None,
)
print(doc.event_id, doc.document_hash, doc.status)

# Convenience: hash + base64 a file, then anchor.
doc = await client.documents.anchor_file(
    file="./invoice.pdf",           # path (str/Path) or raw bytes
    document_ref="Invoice #1042",   # defaults to the filename for a path
    event_type="invoice",
    skip_original=False,            # True = don't upload the original bytes
)

# GET /document — paginated listing (max 500/page).
page = await client.documents.list(
    page=1,
    limit=50,
    date_from=None,
    date_to=None,
    document_ref=None,
)
for item in page.documents:
    print(item.event_id, item.document_ref, item.has_original)

# GET /document/:event_id — fetch one document.
full = await client.documents.get(doc.event_id)
print(full.document_hash, full.has_original)

# GET /document/:event_id/original — download original bytes.
data = await client.documents.get_original(doc.event_id)
with open("recovered.pdf", "wb") as f:
    f.write(data)

# POST /document/:event_id/verify — compare a hash against the anchor.
result = await client.documents.verify(doc.event_id, document_hash="<64-hex sha256>")
print(result.match_result, result.anchored_hash)
```

### AI Attestations

```python
# POST /ai/attestations — anchor an AI attestation.
att = await client.attestations.ingest(
    attestation_type="output",          # "output" | "decision" | "approval"
    input="Summarize this contract",
    output="The contract states...",
    model_provider="anthropic",
    model_name="claude-sonnet-4-20250514",
    model_version="2025-05-14",
    subject={"user_id": "u_42", "session_id": "sess_4f9a"},  # optional
    trace_id=None,
    idempotency_key=None,
)
print(att.attestation_id, att.payload_hash, att.status)

# GET /ai/attestations — paginated listing (max 500/page).
page = await client.attestations.list(
    page=1,
    limit=50,
    date_from=None,
    date_to=None,
    attestation_type=None,
    model_provider=None,
)
for item in page.attestations:
    print(item.attestation_id, item.model_name)

# GET /ai/attestations/:attestation_id — fetch one attestation.
full = await client.attestations.get(att.attestation_id)
print(full.attestation_hash, full.public_key)

# GET /ai/attestations/:attestation_id/raw — original canonical JSON (dict).
raw = await client.attestations.get_raw(att.attestation_id)

# POST /ai/attestations/:attestation_id/verify — compare a hash.
result = await client.attestations.verify(att.attestation_id, content_hash="<64-hex sha256>")
print(result.match_result, result.matched_field)

# Client-side verify by raw payload (str/bytes/dict) — hashes locally, then verifies.
result = await client.attestations.verify_payload(att.attestation_id, payload=raw)

# Client-side Ed25519 signature check — no trust in the server.
sig = await client.attestations.verify_signature(att.attestation_id)
print(sig.valid, sig.reason)
```

> **Note:** for `verify_payload`, pass the raw JSON string exactly as shown in the dashboard's "Raw immutable record" viewer. When passing a `dict`, keys must follow the Rust struct field order (`type`, `payload`, `context`, `subject`) — the backend hashes with `serde_json`, which preserves struct field order rather than sorting.

### Traces

```python
# POST /traces — create a trace.
trace = await client.traces.create(
    label="Batch 2026-07",
    metadata={"source": "nightly"},  # optional
)
print(trace.trace_id, trace.status)

# GET /traces — paginated listing.
page = await client.traces.list(page=1, limit=25, status="open")
for item in page.traces:
    print(item.trace_id, item.label, item.status)

# GET /traces/:trace_id — trace detail with paginated event summaries.
detail = await client.traces.get(trace.trace_id, event_page=1, event_limit=50)
print(detail.event_count, detail.composite_hash)
for ev in detail.events:
    print(ev.event_id, ev.event_type)

# POST /traces/:trace_id/seal — async seal (returns 202; seal runs in background).
sealed = await client.traces.seal(trace.trace_id)
print(sealed.status, sealed.message)

# GET /traces/:trace_id/proof — proof bundle (JSON).
bundle = await client.traces.proof(trace.trace_id)
print(bundle.composite_hash, bundle.verification.all_signatures_valid)

# GET /traces/:trace_id/proof/pdf — proof bundle as PDF bytes.
pdf = await client.traces.proof_pdf(trace.trace_id)
with open("proof.pdf", "wb") as f:
    f.write(pdf)

# DELETE /traces/:trace_id — delete an empty open trace (seal non-empty ones instead).
res = await client.traces.delete(trace.trace_id)
print(res.deleted)
```

### Audit logs

The audit sub-resources (`client.audit.events / orgs / streams / portal_sessions / exports`) return plain `dict`s keyed exactly like the wire JSON.

```python
# ── Orgs — client.audit.orgs ──────────────────────────────
await client.audit.orgs.create(organization_id="org_1", name="Acme")
await client.audit.orgs.list()
await client.audit.orgs.integrity("org_1")                 # seq-gap integrity scan
await client.audit.orgs.set_retention("org_1", days=90)    # clamped to plan cap

# ── Events — client.audit.events ──────────────────────────
event = await client.audit.events.ingest(
    organization_id="org_1",
    action="invoice.approved",
    actor={"type": "user", "id": "u_1"},
    targets=[{"type": "invoice", "id": "inv_9"}],
    occurred_at=None,        # defaults to now (RFC3339, ms + Z)
    context=None,
    metadata=None,
    idempotency_key=None,    # auto-derived from content when omitted (ledger requires one)
)
await client.audit.events.list(organization_id="org_1", limit=100, cursor=None)
await client.audit.events.get(event["event_id"])
await client.audit.events.verify(event["event_id"])        # server-side signature check

# ── Streams — client.audit.streams (SIEM/webhook) ─────────
stream = await client.audit.streams.create("org_1", url="https://siem.example/hook")
# the signing secret is returned ONCE in the response
await client.audit.streams.list("org_1")
await client.audit.streams.test("org_1", stream["id"])     # synthetic delivery
await client.audit.streams.delete("org_1", stream["id"])

# ── Portal sessions — client.audit.portal_sessions ────────
await client.audit.portal_sessions.create(
    organization_id="org_1",
    intent="audit_logs",                 # "audit_logs" | "log_streams"
    session_duration_seconds=7200,       # optional, 60..86400
    link_duration_seconds=300,           # optional, 60..3600
)

# ── Exports — client.audit.exports ────────────────────────
job = await client.audit.exports.create(
    organization_id="org_1",
    format="csv",                        # "csv" | "ndjson"
    filters=None,
)
status = await client.audit.exports.get(job["id"])
# when status["status"] == "ready", status["download_url"] is populated
```

To reuse a stable idempotency key across retries of an identical event body, derive one with the exported helper:

```python
from invoance import content_idempotency_key

body = {"organization_id": "org_1", "action": "invoice.approved",
        "actor": {"type": "user", "id": "u_1"}, "targets": []}
key = content_idempotency_key(body)
await client.audit.events.ingest(**body, idempotency_key=key)
```

## Offline verification

Verify signatures entirely client-side, without trusting the server's answer.

Audit events (`verify_audit_event`, exported from the package root):

```python
from invoance import verify_audit_event

event = await client.audit.events.get("evt_123")
result = verify_audit_event(event)
print(result.valid, result.reason, result.payload_hash, result.key_source)

# Pin the tenant's registered key for a real tamper guarantee (not the row's embedded key):
result = verify_audit_event(event, public_key="<tenant pubkey hex>")
```

`verify_audit_event` returns an `AuditVerifyResult(valid, reason, payload_hash, key_source)`. With no `public_key` it checks against the key embedded in the event (`key_source="event"`); passing `public_key` pins your known key (`key_source="pinned"`).

AI attestations verify two ways client-side:

```python
# By payload — hashes the raw canonical JSON locally, then verifies.
result = await client.attestations.verify_payload(att.attestation_id, payload=raw)

# By Ed25519 signature — checks signature + public_key with no server trust.
sig = await client.attestations.verify_signature(att.attestation_id)
print(sig.valid, sig.reason)
```

Both offline verifiers require the `nacl` (PyNaCl) dependency, which ships with the SDK.

## Error handling

Every error the SDK raises — API responses, network failures, client-side validation — inherits from `InvoanceError`:

```python
from invoance import (
    InvoanceClient,
    InvoanceError,
    AuthenticationError,
    QuotaExceededError,
    ValidationError,
    TimeoutError,
    NetworkError,
)

try:
    await client.events.ingest(event_type="user.login", payload={...})
except AuthenticationError:
    ...  # 401 — bad API key
except QuotaExceededError as e:
    print(f"rate limited, retry in {e.retry_after_seconds}s")
except ValidationError:
    ...  # 400 from server, or client-side input validation failure
except TimeoutError:
    ...  # request exceeded configured timeout
except NetworkError:
    ...  # DNS/connection/TLS failure before a response
except InvoanceError:
    ...  # any other API or transport failure
```

The full exception set is exported from `invoance`: `InvoanceError`, `AuthenticationError`, `ForbiddenError`, `NotFoundError`, `QuotaExceededError`, `ValidationError`, `ConflictError`, `ServerError`, `NetworkError`, `TimeoutError`.

Common hex-SHA-256 fields (`document_hash`, `payload_hash`, `content_hash`) are validated client-side — passing a malformed hash raises `ValidationError` before a request is sent.

## Examples

```bash
pip install invoance[examples]
python examples/quickstart.py
```

See the `examples/` directory for complete working examples covering events, documents, AI attestations, traces, and audit logs.

## License

MIT
