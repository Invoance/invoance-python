"""Add an event to an existing open trace.

Events are the building blocks of a trace. Each event is individually
hashed and signed, then linked to the trace by its trace_id. Once the
trace is sealed, all events become part of a single cryptographic proof.

Usage
-----
    python examples/traces/add_event_to_trace.py <trace_id>
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/traces/add_event_to_trace.py <trace_id>")
        sys.exit(1)

    trace_id = sys.argv[1]

    async with InvoanceClient() as client:
        # Anchor an event to the trace
        event = await client.events.ingest(
            event_type="contract.signed",
            payload={
                "contract_id": "CTR-2026-04221",
                "signed_by": "legal@acme.comsdd",
                "counterparty": "vendor@example.com",
            },
            trace_id=trace_id,
        )

        print(f"event_id:    {event.event_id}")
        print(f"ingested_at: {event.ingested_at}")
        print(f"trace_id:    {trace_id}")
        print("\nEvent anchored to trace. Note: events are processed")
        print("asynchronously — it may take a moment to appear in the trace.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
