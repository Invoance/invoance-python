"""Ingest a compliance event into the append-only ledger.

Usage
-----
    python examples/events/ingest_event.py
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    async with InvoanceClient() as client:
        result = await client.events.ingest(
            event_type="policy.approval",
            payload={
                "policy_id": "pol_8472",
                "approved_by": "risk_committee",
                "decision": "approved",
            },
        )
        print(f"event_id:    {result.event_id}")
        print(f"ingested_at: {result.ingested_at}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
