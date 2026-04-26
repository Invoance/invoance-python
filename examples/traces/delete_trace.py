"""Delete an empty open trace.

Only traces with status 'open' and zero events can be deleted.
Traces that contain events should be sealed instead.

Usage
-----
    python examples/traces/delete_trace.py <trace_id>
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import ConflictError, InvoanceError, NotFoundError

load_dotenv()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/traces/delete_trace.py <trace_id>")
        sys.exit(1)

    trace_id = sys.argv[1]

    async with InvoanceClient() as client:
        try:
            result = await client.traces.delete(trace_id)
        except NotFoundError:
            print(f"Trace {trace_id} not found.")
            return
        except ConflictError as e:
            print(f"Cannot delete: {e}")
            return

        print(f"trace_id: {result.trace_id}")
        print(f"deleted:  {result.deleted}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
