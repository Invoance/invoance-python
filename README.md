# Invoance Python SDK

Official Python SDK for the [Invoance](https://invoance.com) compliance API — cryptographic proof, document anchoring, and AI attestation.

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

Common hex-SHA-256 fields (`document_hash`, `payload_hash`, `content_hash`) are validated client-side — passing a malformed hash raises `ValidationError` before a request is sent.

## Examples

```bash
pip install invoance[examples]
python examples/quickstart.py
```

See the `examples/` directory for complete working examples covering events, documents, AI attestations, and traces.

## License

MIT
