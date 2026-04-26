"""Verify an event — by hash or by re-submitting the original payload.

Usage
-----
    python examples/events/verify_event.py <event_id> '<payload_json>'

Example
-------
    python examples/events/verify_event.py a0f43089-4cfc-483e-a8e5-57c10130fcfc \
        '{"policy_id":"pol_8472","approved_by":"risk_committee","decision":"approved"}'
"""

import asyncio
import hashlib
import json
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    if len(sys.argv) < 3:
        print("Usage: python verify_event.py <event_id> '<payload_json>'\n")
        print("Example:")
        print('  python verify_event.py a0f43089-... \'{"policy_id":"pol_8472","decision":"approved"}\'')

        sys.exit(1)

    event_id = sys.argv[1]
    raw_json = " ".join(sys.argv[2:])
    payload = json.loads(raw_json)

    async with InvoanceClient() as client:

        # ── Verify by re-submitting the raw payload ──
        r1 = await client.events.verify(
            event_id,
            payload=payload,
        )
        print("── Verify by payload ──")
        print(f"  match_result: {r1.match_result}")
        print(f"  method:       {r1.method}")
        print(f"  anchored_at:  {r1.anchored_at}")

        # ── Verify by pre-computed hash ──
        payload_hash = hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()

        r2 = await client.events.verify(
            event_id,
            payload_hash=payload_hash,
        )
        print("\n── Verify by hash ──")
        print(f"  match_result:   {r2.match_result}")
        print(f"  method:         {r2.method}")
        print(f"  anchored_hash:  {r2.anchored_hash}")
        print(f"  submitted_hash: {r2.submitted_hash}")

        org = r2.organization
        if org:
            print(f"\n── Issuer ──")
            print(f"  name:            {org.name}")
            print(f"  issuer_name:     {org.issuer_name}")
            print(f"  domain:          {org.primary_domain}")
            print(f"  domain_verified: {org.domain_verified}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
