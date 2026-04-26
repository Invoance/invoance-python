"""Complete end-to-end trace workflow:

1. Create a trace
2. Ingest 3 events with trace_id
3. Seal the trace
4. Poll until sealed
5. Export the proof bundle

Usage
-----
    python examples/traces/full_workflow.py
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    client = InvoanceClient()

    async with client:
        print("Step 1: Creating trace...")
        trace = await client.traces.create(
            label="Invoice Processing — Q1 2026",
            metadata={
                "quarter": "Q1",
                "year": 2026,
                "department": "finance",
            },
        )
        trace_id = trace.trace_id
        print(f"  Created: {trace_id}\n")

        print("Step 2: Ingesting events...")
        event1 = await client.events.ingest(
            event_type="invoice.received",
            payload={"invoice_number": "INV-2026-001", "amount": 5000},
            trace_id=trace_id,
        )
        print(f"  Event 1 (invoice.received): {event1.event_id}")

        event2 = await client.events.ingest(
            event_type="invoice.approved",
            payload={"invoice_number": "INV-2026-001", "approved_by": "manager@acme.com"},
            trace_id=trace_id,
        )
        print(f"  Event 2 (invoice.approved): {event2.event_id}")

        event3 = await client.events.ingest(
            event_type="payment.authorized",
            payload={"invoice_number": "INV-2026-001", "payment_id": "PAY-2026-0001"},
            trace_id=trace_id,
        )
        print(f"  Event 3 (payment.authorized): {event3.event_id}\n")

        print("Step 3: Sealing trace...")
        await client.traces.seal(trace_id)
        print("  Seal request sent (async)\n")

        print("Step 4: Polling for completion (max 30 seconds)...")
        sealed_trace = await client.traces.get(trace_id)
        attempts = 0
        max_attempts = 15

        while sealed_trace.status != "sealed" and attempts < max_attempts:
            print(f"  Status: {sealed_trace.status} ({attempts + 1}/{max_attempts})...")
            await asyncio.sleep(2)
            sealed_trace = await client.traces.get(trace_id)
            attempts += 1

        if sealed_trace.status == "sealed":
            print("  Status: sealed (completed)\n")
        else:
            print(f"  Timeout: trace not sealed after {attempts * 2} seconds")
            return

        print("Step 5: Exporting proof bundle...")
        proof = await client.traces.proof(trace_id)
        print(f"  Version:       {proof.version}")
        print(f"  Event count:   {proof.event_count}")
        print(f"  Composite hash: {proof.composite_hash[:32]}...\n")

        print("── Summary ──")
        print(f"Trace ID:    {proof.trace_id}")
        print(f"Label:       {proof.label}")
        print(f"Status:      {proof.status}")
        print(f"Events:      {proof.event_count}")
        print(f"Created:     {proof.created_at}")
        print(f"Sealed:      {proof.sealed_at}")
        print(f"Domain:      {proof.tenant_domain}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
