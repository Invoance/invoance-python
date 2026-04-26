"""Create a new trace with label and metadata.

Usage
-----
    python examples/traces/create_trace.py
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import ConflictError, InvoanceError

load_dotenv()


async def main():
    async with InvoanceClient() as client:
        try:
            trace = await client.traces.create(
                label="Vendor Onboarding — Acme Corpss",
                metadata={
                    "department": "procurement",
                    "initiated_by": "j.smith@acme.com",
                },
            )
        except ConflictError:
            print("An open trace with this label already exists.")
            print("Seal or delete the existing trace before creating a new one.")
            return

        print(f"trace_id:  {trace.trace_id}")
        print(f"status:    {trace.status}")
        print(f"created_at: {trace.created_at}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
