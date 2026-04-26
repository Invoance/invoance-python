"""Get a single trace by ID and print its details.

Usage
-----
    python examples/traces/get_trace.py <trace_id>

Example
-------
    python examples/traces/get_trace.py tr_a1b2c3d4e5f6
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    trace_id = sys.argv[1] if len(sys.argv) > 1 else os.getenv("TRACE_ID")

    if not trace_id:
        print("Usage: python get_trace.py <trace_id>")
        print("       Or set TRACE_ID environment variable")
        sys.exit(1)

    async with InvoanceClient() as client:
        trace = await client.traces.get(trace_id)

        print(f"trace_id:       {trace.trace_id}")
        print(f"label:          {trace.label}")
        print(f"status:         {trace.status}")
        print(f"event_count:    {trace.event_count or 0}")
        print(f"created_at:     {trace.created_at}")
        print(f"sealed_at:      {trace.sealed_at or 'not sealed'}")

        if trace.composite_hash:
            print(f"composite_hash: {trace.composite_hash[:32]}...")

        if trace.events:
            print("\n── Events ──")
            for event in trace.events:
                print(f"  {event.event_type} ({event.event_id[:16]}...)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
