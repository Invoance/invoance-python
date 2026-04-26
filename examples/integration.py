"""Integration examples — hit the REAL backend.

Usage
-----
    # From sdk/invoance-python/:
    python examples/integration.py

    # Or from inside examples/:
    python integration.py

Requires a running backend and a valid API key in .env:
    INVOANCE_API_KEY=invoance_live_...
    INVOANCE_BASE_URL=http://localhost:33100

NOTE: The backend uses async ingestion (NATS JetStream -> Postgres).
      Write endpoints return immediately, but the data may not be
      queryable for a short period. Examples use `wait_for()` to poll
      GET endpoints until the record is available.
"""

import asyncio
import hashlib
import os
import sys
import uuid
import traceback

from dotenv import load_dotenv

from invoance import (
    InvoanceClient,
    AuthenticationError,
    NotFoundError,
    QuotaExceededError,
)
from invoance.errors import InvoanceError

# ── Config ────────────────────────────────────────────────────

load_dotenv()

API_KEY = os.environ.get("INVOANCE_API_KEY", "")
BASE_URL = os.environ.get("INVOANCE_BASE_URL", "http://localhost:33100")

POLL_INTERVAL = 0.5   # seconds between retries
POLL_TIMEOUT = 30.0   # max seconds to wait
THROTTLE = 0.3        # seconds between examples to avoid rate limits


# ── Helpers ───────────────────────────────────────────────────

async def wait_for(coro_factory, timeout=POLL_TIMEOUT, interval=POLL_INTERVAL):
    """Retry an async callable until it succeeds or timeout is reached.

    The backend publishes to NATS and a consumer writes to Postgres
    asynchronously. This helper polls until the record appears.
    """
    elapsed = 0.0
    last_exc = None
    while elapsed < timeout:
        try:
            return await coro_factory()
        except (NotFoundError, InvoanceError, AssertionError, QuotaExceededError) as exc:
            last_exc = exc
            await asyncio.sleep(interval)
            elapsed += interval
    raise last_exc  # type: ignore[misc]


async def retry_on_429(coro_factory, retries=5, backoff=0.5):
    """Retry an async call when rate-limited (429).

    Developer plan allows 10 req/s. When examples fire in bursts
    the limiter can reject requests. A short backoff is enough.
    """
    for attempt in range(retries):
        try:
            return await coro_factory()
        except QuotaExceededError:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(backoff * (attempt + 1))


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── Events ────────────────────────────────────────────────────

async def example_ingest_event(client: InvoanceClient):
    """POST /v1/events — ingest and get back event_id."""
    result = await client.events.ingest(
        event_type="sdk.integration_test",
        payload={"test_run": str(uuid.uuid4()), "action": "login"},
    )
    assert result.event_id, "Should return an event_id"
    assert result.ingested_at, "Should return ingested_at timestamp"
    print(f"  ✓ Ingested event: {result.event_id}")


async def example_ingest_and_get_event(client: InvoanceClient):
    """POST then GET /v1/events/:id — round-trip (waits for async persist)."""
    payload = {"user": "test_user", "action": "signup", "run": str(uuid.uuid4())}
    ingest = await client.events.ingest(
        event_type="sdk.integration_test",
        payload=payload,
    )

    event = await wait_for(lambda: client.events.get(ingest.event_id))
    assert event.event_id == ingest.event_id
    assert event.event_type == "sdk.integration_test"
    assert event.payload == payload
    assert event.payload_hash, "Should have payload_hash"
    print(f"  ✓ GET event: {event.event_id} | hash: {event.payload_hash[:16]}...")


async def example_list_events(client: InvoanceClient):
    """GET /v1/events — paginated list."""
    await client.events.ingest(
        event_type="sdk.integration_test",
        payload={"list_test": True},
    )

    async def _poll():
        result = await client.events.list(page=1, limit=5)
        assert result.total >= 1
        return result

    result = await wait_for(_poll)
    assert len(result.events) >= 1
    assert result.page == 1
    assert result.limit == 5
    print(f"  ✓ Listed events: {result.total} total, got {len(result.events)}")


async def example_list_events_with_filter(client: InvoanceClient):
    """GET /v1/events?event_type=... — filtered list."""
    unique_type = f"sdk.filter_test.{uuid.uuid4().hex[:8]}"
    ingest = await client.events.ingest(event_type=unique_type, payload={"x": 1})

    # Wait for the event to land in Postgres (uncached GET)
    await wait_for(lambda: client.events.get(ingest.event_id))

    # Now poll the list — may need to wait for Redis cache (30s TTL) to expire
    async def _poll():
        result = await client.events.list(event_type=unique_type, limit=10)
        assert result.total >= 1
        return result

    result = await wait_for(_poll, timeout=35.0)
    for ev in result.events:
        assert ev.event_type == unique_type
    print(f"  ✓ Filtered list: {result.total} events of type {unique_type}")


async def example_verify_event_by_payload(client: InvoanceClient):
    """POST /v1/events/:id/verify — verify using raw payload."""
    payload = {"verify_test": str(uuid.uuid4()), "value": 42}
    ingest = await retry_on_429(lambda: client.events.ingest(
        event_type="sdk.verify_test",
        payload=payload,
    ))

    await wait_for(lambda: client.events.get(ingest.event_id))

    result = await retry_on_429(lambda: client.events.verify(
        ingest.event_id,
        payload=payload,
    ))
    assert result.match_result is True, "Payload should match"
    assert result.method == "payload"
    assert result.event_id == ingest.event_id
    print(f"  ✓ Verify by payload: match={result.match_result}, field={result.matched_field}")


async def example_verify_event_by_hash(client: InvoanceClient):
    """POST /v1/events/:id/verify — verify using payload_hash."""
    payload = {"hash_test": str(uuid.uuid4())}
    ingest = await retry_on_429(lambda: client.events.ingest(
        event_type="sdk.verify_test",
        payload=payload,
    ))

    event = await wait_for(lambda: client.events.get(ingest.event_id))

    result = await retry_on_429(lambda: client.events.verify(
        ingest.event_id,
        payload_hash=event.payload_hash,
    ))
    assert result.match_result is True
    assert result.method == "hash"
    print(f"  ✓ Verify by hash: match={result.match_result}")


async def example_verify_event_mismatch(client: InvoanceClient):
    """POST /v1/events/:id/verify — wrong hash returns match_result=False."""
    ingest = await retry_on_429(lambda: client.events.ingest(
        event_type="sdk.verify_test",
        payload={"mismatch": True},
    ))

    await wait_for(lambda: client.events.get(ingest.event_id))

    fake_hash = hashlib.sha256(b"wrong data").hexdigest()
    result = await retry_on_429(lambda: client.events.verify(
        ingest.event_id,
        payload_hash=fake_hash,
    ))
    assert result.match_result is False
    print(f"  ✓ Verify mismatch: match={result.match_result}")


# ── Documents ─────────────────────────────────────────────────

async def example_anchor_document(client: InvoanceClient):
    """POST /v1/document/anchor — anchor a document hash."""
    doc_content = f"Contract v{uuid.uuid4().hex[:8]}".encode()
    doc_hash = _hash(doc_content)

    result = await retry_on_429(lambda: client.documents.anchor(
        document_hash=doc_hash,
        document_ref="test-contract.pdf",
    ))
    assert result.event_id, "Should return event_id"
    assert result.status == "accepted"
    assert result.document_hash == doc_hash
    print(f"  ✓ Anchored document: {result.event_id}")


async def example_anchor_and_get_document(client: InvoanceClient):
    """POST then GET /v1/document/:id — round-trip."""
    doc_content = f"Invoice {uuid.uuid4().hex[:8]}".encode()
    doc_hash = _hash(doc_content)

    anchor = await retry_on_429(lambda: client.documents.anchor(
        document_hash=doc_hash,
        document_ref="test-invoice.pdf",
        metadata={"amount": 1500, "currency": "USD"},
    ))

    doc = await wait_for(lambda: client.documents.get(anchor.event_id))
    assert doc.event_id == anchor.event_id
    assert doc.document_hash == doc_hash
    assert doc.document_ref == "test-invoice.pdf"
    assert doc.signature_b64, "Should have a cryptographic signature"
    print(f"  ✓ GET document: {doc.event_id} | sig: {doc.signature_b64[:20]}...")


async def example_list_documents(client: InvoanceClient):
    """GET /v1/document — paginated list."""
    doc_hash = _hash(f"list-test-{uuid.uuid4()}".encode())
    await retry_on_429(lambda: client.documents.anchor(
        document_hash=doc_hash,
        document_ref="list-test.pdf",
    ))

    async def _poll():
        result = await client.documents.list(page=1, limit=5)
        assert result.total >= 1
        return result

    result = await wait_for(_poll)
    assert len(result.documents) >= 1
    print(f"  ✓ Listed documents: {result.total} total, got {len(result.documents)}")


async def example_verify_document_match(client: InvoanceClient):
    """POST /v1/document/:id/verify — matching hash."""
    doc_content = f"Verify me {uuid.uuid4()}".encode()
    doc_hash = _hash(doc_content)

    anchor = await retry_on_429(lambda: client.documents.anchor(
        document_hash=doc_hash,
        document_ref="verify-test.pdf",
    ))

    await wait_for(lambda: client.documents.get(anchor.event_id))

    result = await retry_on_429(lambda: client.documents.verify(
        anchor.event_id, document_hash=doc_hash,
    ))
    assert result.match_result is True
    assert result.anchored_hash == doc_hash
    assert result.submitted_hash == doc_hash
    print(f"  ✓ Verify document match: {result.match_result}")


async def example_verify_document_mismatch(client: InvoanceClient):
    """POST /v1/document/:id/verify — wrong hash."""
    doc_hash = _hash(f"real-{uuid.uuid4()}".encode())
    anchor = await retry_on_429(lambda: client.documents.anchor(
        document_hash=doc_hash,
        document_ref="mismatch-test.pdf",
    ))

    await wait_for(lambda: client.documents.get(anchor.event_id))

    fake_hash = _hash(b"tampered document")
    result = await retry_on_429(lambda: client.documents.verify(
        anchor.event_id, document_hash=fake_hash,
    ))
    assert result.match_result is False
    print(f"  ✓ Verify document mismatch: {result.match_result}")


# ── AI Attestations ───────────────────────────────────────────

async def example_ingest_attestation(client: InvoanceClient):
    """POST /v1/ai/attestations — ingest an AI attestation."""
    result = await retry_on_429(lambda: client.attestations.ingest(
        attestation_type="output",
        input="What is 2+2?",
        output="2+2 equals 4.",
        model_provider="openai",
        model_name="gpt-4o",
        model_version="2024-08-06",
        subject={
            "user_id": "test-user",
            "session_id": f"sess-{uuid.uuid4().hex[:8]}",
        },
    ))
    assert result.attestation_id, "Should return attestation_id"
    assert result.status == "accepted"
    assert result.input_hash, "Should return input_hash"
    assert result.output_hash, "Should return output_hash"
    assert result.payload_hash, "Should return payload_hash"
    print(f"  ✓ Ingested attestation: {result.attestation_id}")


async def example_ingest_and_get_attestation(client: InvoanceClient):
    """POST then GET /v1/ai/attestations/:id — round-trip."""
    nonce = uuid.uuid4().hex[:8]
    ingest = await retry_on_429(lambda: client.attestations.ingest(
        attestation_type="decision",
        input=f"Should we approve loan #12345? [run:{nonce}]",
        output=f"Approved based on credit score 780. [run:{nonce}]",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        model_version="2025-04-14",
    ))

    att = await wait_for(lambda: client.attestations.get(ingest.attestation_id))
    assert att.attestation_id == ingest.attestation_id
    assert att.attestation_type == "decision"
    assert att.model_provider == "anthropic"
    assert att.model_name == "claude-sonnet-4-20250514"
    assert att.signature, "Should have cryptographic signature"
    print(f"  ✓ GET attestation: {att.attestation_id} | type={att.attestation_type}")


async def example_list_attestations(client: InvoanceClient):
    """GET /v1/ai/attestations — paginated list."""
    await retry_on_429(lambda: client.attestations.ingest(
        attestation_type="output",
        input="test input",
        output="test output",
        model_provider="test",
        model_name="test-model",
        model_version="1.0",
    ))

    async def _poll():
        result = await client.attestations.list(page=1, limit=5)
        assert result.total >= 1
        return result

    result = await wait_for(_poll)
    assert len(result.attestations) >= 1
    print(f"  ✓ Listed attestations: {result.total} total, got {len(result.attestations)}")


async def example_list_attestations_with_filter(client: InvoanceClient):
    """GET /v1/ai/attestations?attestation_type=... — filtered."""
    nonce = uuid.uuid4().hex[:8]
    ingest = await retry_on_429(lambda: client.attestations.ingest(
        attestation_type="approval",
        input=f"Approve deployment? [run:{nonce}]",
        output=f"Approved. [run:{nonce}]",
        model_provider="internal",
        model_name="policy-engine",
        model_version="3.1",
    ))

    await wait_for(lambda: client.attestations.get(ingest.attestation_id))

    async def _poll():
        result = await client.attestations.list(attestation_type="approval", limit=10)
        assert result.total >= 1
        return result

    result = await wait_for(_poll, timeout=35.0)
    for att in result.attestations:
        assert att.attestation_type == "approval"
    print(f"  ✓ Filtered attestations: {result.total} of type 'approval'")


async def example_verify_attestation_match(client: InvoanceClient):
    """POST /v1/ai/attestations/:id/verify — matching hash."""
    nonce = uuid.uuid4().hex[:8]
    ingest = await retry_on_429(lambda: client.attestations.ingest(
        attestation_type="output",
        input=f"Summarize this. [run:{nonce}]",
        output=f"Here is the summary. [run:{nonce}]",
        model_provider="openai",
        model_name="gpt-4o",
        model_version="2024-08-06",
    ))

    await wait_for(lambda: client.attestations.get(ingest.attestation_id))

    result = await retry_on_429(lambda: client.attestations.verify(
        ingest.attestation_id,
        content_hash=ingest.payload_hash,
    ))
    assert result.match_result is True
    print(f"  ✓ Verify attestation match: field={result.matched_field}")


async def example_verify_attestation_mismatch(client: InvoanceClient):
    """POST /v1/ai/attestations/:id/verify — wrong hash."""
    nonce = uuid.uuid4().hex[:8]
    ingest = await retry_on_429(lambda: client.attestations.ingest(
        attestation_type="output",
        input=f"test [run:{nonce}]",
        output=f"test output [run:{nonce}]",
        model_provider="test",
        model_name="test-model",
        model_version="1.0",
    ))

    await wait_for(lambda: client.attestations.get(ingest.attestation_id))

    fake_hash = hashlib.sha256(b"wrong content").hexdigest()
    result = await retry_on_429(lambda: client.attestations.verify(
        ingest.attestation_id,
        content_hash=fake_hash,
    ))
    assert result.match_result is False
    print(f"  ✓ Verify attestation mismatch: match={result.match_result}")


# ── Error Handling ────────────────────────────────────────────

async def example_bad_api_key():
    """401 — invalid API key raises AuthenticationError."""
    bad_client = InvoanceClient(
        api_key="invoance_live_invalid_key_000000",
    )
    try:
        await bad_client.events.list()
        raise AssertionError("Should have raised AuthenticationError")
    except AuthenticationError as e:
        assert e.status_code == 401
        print(f"  ✓ Bad API key -> AuthenticationError (401)")
    finally:
        await bad_client.close()


async def example_event_not_found(client: InvoanceClient):
    """404 — non-existent event raises NotFoundError."""
    fake_id = str(uuid.uuid4())
    try:
        await client.events.get(fake_id)
        raise AssertionError("Should have raised NotFoundError")
    except NotFoundError:
        print(f"  ✓ Missing event -> NotFoundError (404)")


async def example_document_not_found(client: InvoanceClient):
    """404 — non-existent document raises NotFoundError."""
    fake_id = str(uuid.uuid4())
    try:
        await client.documents.get(fake_id)
        raise AssertionError("Should have raised NotFoundError")
    except NotFoundError:
        print(f"  ✓ Missing document -> NotFoundError (404)")


async def example_attestation_not_found(client: InvoanceClient):
    """404 — non-existent attestation raises NotFoundError."""
    fake_id = str(uuid.uuid4())
    try:
        await client.attestations.get(fake_id)
        raise AssertionError("Should have raised NotFoundError")
    except NotFoundError:
        print(f"  ✓ Missing attestation -> NotFoundError (404)")


# ── Runner ────────────────────────────────────────────────────

ALL_EXAMPLES = [
    # (section_name, [(name, coro_factory, needs_client), ...])
    ("Events", [
        ("ingest_event", example_ingest_event, True),
        ("ingest_and_get_event", example_ingest_and_get_event, True),
        ("list_events", example_list_events, True),
        ("list_events_with_filter", example_list_events_with_filter, True),
        ("verify_event_by_payload", example_verify_event_by_payload, True),
        ("verify_event_by_hash", example_verify_event_by_hash, True),
        ("verify_event_mismatch", example_verify_event_mismatch, True),
    ]),
    ("Documents", [
        ("anchor_document", example_anchor_document, True),
        ("anchor_and_get_document", example_anchor_and_get_document, True),
        ("list_documents", example_list_documents, True),
        ("verify_document_match", example_verify_document_match, True),
        ("verify_document_mismatch", example_verify_document_mismatch, True),
    ]),
    ("AI Attestations", [
        ("ingest_attestation", example_ingest_attestation, True),
        ("ingest_and_get_attestation", example_ingest_and_get_attestation, True),
        ("list_attestations", example_list_attestations, True),
        ("list_attestations_with_filter", example_list_attestations_with_filter, True),
        ("verify_attestation_match", example_verify_attestation_match, True),
        ("verify_attestation_mismatch", example_verify_attestation_mismatch, True),
    ]),
    ("Error Handling", [
        ("bad_api_key", example_bad_api_key, False),
        ("event_not_found", example_event_not_found, True),
        ("document_not_found", example_document_not_found, True),
        ("attestation_not_found", example_attestation_not_found, True),
    ]),
]


async def run_all():
    """Run every integration example against the live backend."""
    if not API_KEY:
        print("✗ INVOANCE_API_KEY not set. Copy .env.example -> .env and fill it in.")
        sys.exit(1)

    print(f"Running integration examples against {BASE_URL}")
    print(f"API key: {API_KEY[:20]}...{API_KEY[-4:]}\n")

    passed = 0
    failed = 0
    errors: list[tuple[str, Exception]] = []

    async with InvoanceClient() as client:
        for section, examples in ALL_EXAMPLES:
            print(f"── {section} ──")
            for name, fn, needs_client in examples:
                try:
                    if needs_client:
                        await fn(client)
                    else:
                        await fn()
                    passed += 1
                except Exception as e:
                    failed += 1
                    errors.append((name, e))
                    print(f"  ✗ {name}: {e}")
                await asyncio.sleep(THROTTLE)
            print()

    print("══════════════════════════════════")
    print(f"  {passed} passed, {failed} failed")
    print("══════════════════════════════════")

    if errors:
        print("\nFailures:")
        for name, exc in errors:
            print(f"\n  {name}:")
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all())
