"""Quickstart – exercise every endpoint against a local backend."""

import asyncio
import hashlib
import json
import sys

from invoance import InvoanceClient
from invoance.errors import InvoanceError


async def main() -> None:
    async with InvoanceClient() as client:

        # ── Events ───────────────────────────────────────────
        print("=== Events ===")

        event = await client.events.ingest(
            event_type="user.login",
            payload={"user_id": "u_42", "ip": "192.168.1.1"},
        )
        print(f"  Ingested event: {event.event_id}")

        fetched = await client.events.get(event.event_id)
        print(f"  Fetched event type: {fetched.event_type}")

        listing = await client.events.list(limit=5)
        print(f"  Listed events: {listing.total} total, page {listing.page}")

        verification = await client.events.verify(
            event.event_id,
            payload={"user_id": "u_42", "ip": "192.168.1.1"},
        )
        print(f"  Verify match: {verification.match_result} ({verification.method})")

        # ── Documents ────────────────────────────────────────
        print("\n=== Documents ===")

        content = b"Hello, Invoance!"
        doc_hash = hashlib.sha256(content).hexdigest()

        doc = await client.documents.anchor(
            document_hash=doc_hash,
            document_ref="hello.txt",
            event_type="document_upload",
        )
        print(f"  Anchored document: {doc.event_id}")

        doc_detail = await client.documents.get(doc.event_id)
        print(f"  Document ref: {doc_detail.document_ref}")

        doc_list = await client.documents.list(limit=5)
        print(f"  Listed docs: {doc_list.total} total")

        doc_verify = await client.documents.verify(
            doc.event_id,
            document_hash=doc_hash,
        )
        print(f"  Verify match: {doc_verify.match_result}")

        # ── AI Attestations ──────────────────────────────────
        print("\n=== AI Attestations ===")

        att = await client.attestations.ingest(
            attestation_type="output",
            input="What is 2+2?",
            output="4",
            model_provider="openai",
            model_name="gpt-4o",
            model_version="2025-01-01",
            subject={"user_id": "u_42"},
        )
        print(f"  Attestation: {att.attestation_id}")

        att_detail = await client.attestations.get(att.attestation_id)
        print(f"  Type: {att_detail.attestation_type}, hash: {att_detail.attestation_hash[:16]}...")

        att_list = await client.attestations.list(limit=5)
        print(f"  Listed attestations: {att_list.total} total")

        att_verify = await client.attestations.verify(
            att.attestation_id,
            content_hash=att.payload_hash,
        )
        print(f"  Verify match: {att_verify.match_result}")

        print("\nDone.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
