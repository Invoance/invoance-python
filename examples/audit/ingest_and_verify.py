"""Audit Logs: ingest an event, read it back, and verify its signature OFFLINE.

Usage
-----
    python examples/audit/ingest_and_verify.py <org_external_id>

The org must already exist (``client.audit.orgs.create(external_id=...)``). The event is
signed server-side; we read it back and check the Ed25519 signature client-side with
``verify_audit_event`` — no second network round-trip is needed to trust the row.
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient, verify_audit_event
from invoance.errors import InvoanceError

load_dotenv()


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python examples/audit/ingest_and_verify.py <org_external_id>")
        sys.exit(1)
    org = sys.argv[1]

    async with InvoanceClient() as client:
        # occurred_at defaults to now and the Idempotency-Key is auto-derived from the
        # event content, so a bare ingest() just works. For idempotent retries, pin both
        # occurred_at and idempotency_key=content_idempotency_key(your_full_body).
        created = await client.audit.events.ingest(
            org=org,
            action="user.signed_in",
            actor={"type": "user", "id": "u_42", "name": "Ada Lovelace"},
            targets=[{"type": "doc", "id": "d_1"}],
        )
        event_id = created["event_id"]
        print(f"ingested {event_id}")

        # The signer is async; poll the read until the row is persisted.
        event = None
        for _ in range(20):
            try:
                event = await client.audit.events.get(event_id)
                break
            except InvoanceError:
                await asyncio.sleep(0.5)
        if event is None:
            print("event did not persist in time")
            sys.exit(1)

        # Verify OFFLINE: reconstruct the canonical bytes + check the signature.
        result = verify_audit_event(event)
        print(f"offline verify: valid={result.valid} reason={result.reason} key_source={result.key_source}")

        # For a real tamper guarantee, pin the tenant's registered key:
        #   result = verify_audit_event(event, public_key="<tenant pubkey hex>")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
