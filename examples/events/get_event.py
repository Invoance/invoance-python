"""Retrieve a single event by ID.

Usage
-----
    python examples/events/get_event.py <event_id>
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python get_event.py <event_id>")
        sys.exit(1)

    event_id = sys.argv[1]

    async with InvoanceClient() as client:
        event = await client.events.get(event_id)
        print(f"event_id:     {event.event_id}")
        print(f"event_type:   {event.event_type}")
        print(f"payload_hash: {event.payload_hash}")
        print(f"event_hash:   {event.event_hash}")
        print(f"ingested_at:  {event.ingested_at}")
        print(f"payload:      {event.payload}")

        if event.organization:
            org = event.organization
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
