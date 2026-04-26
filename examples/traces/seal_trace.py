"""Seal a trace (async operation, returns 202).

Usage
-----
    python examples/traces/seal_trace.py <trace_id>

Example
-------
    python examples/traces/seal_trace.py tr_a1b2c3d4e5f6
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
        print("Usage: python seal_trace.py <trace_id>")
        print("       Or set TRACE_ID environment variable")
        sys.exit(1)

    async with InvoanceClient() as client:
        result = await client.traces.seal(trace_id)

        print(f"status:  {result.status}")
        print(f"message: {result.message}")
        print("")
        print("Note: Sealing is asynchronous. Use get_trace.py to poll the")
        print("      trace status until it transitions to 'sealed'.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
