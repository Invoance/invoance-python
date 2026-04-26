"""List open traces with pagination.

Usage
-----
    python examples/traces/list_traces.py
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    async with InvoanceClient() as client:
        result = await client.traces.list(
            page=1,
            limit=10,
            status="open",
        )

        print(f"Total traces: {result.total}")
        print(f"Page: {result.page}, Limit: {result.limit}")
        print(f"Has more: {result.has_more}")
        print("")

        for trace in result.traces:
            print(f"trace_id:  {trace.trace_id}")
            print(f"label:     {trace.label}")
            print(f"status:    {trace.status}")
            print(f"events:    {trace.event_count or 0}")
            print("")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
