"""Paginated event listing with optional filters.

Usage
-----
    python examples/events/list_events.py
    python examples/events/list_events.py --limit 5
    python examples/events/list_events.py --limit 20 --page 2 --event-type policy.approval
    python examples/events/list_events.py --date-from 2025-01-01 --date-to 2025-12-31
"""

import argparse
import asyncio

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


def parse_args():
    p = argparse.ArgumentParser(description="List compliance events")
    p.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    p.add_argument("--limit", type=int, default=10, help="Results per page (default: 10)")
    p.add_argument("--event-type", default=None, help="Filter by event type")
    p.add_argument("--date-from", default=None, help="Start date filter (YYYY-MM-DD)")
    p.add_argument("--date-to", default=None, help="End date filter (YYYY-MM-DD)")
    return p.parse_args()


async def main():
    args = parse_args()

    async with InvoanceClient() as client:
        page = await client.events.list(
            page=args.page,
            limit=args.limit,
            event_type=args.event_type,
            date_from=args.date_from,
            date_to=args.date_to,
        )
        print(f"Total events: {page.total}")
        print(f"Page {page.page}, has_more: {page.has_more}\n")

        for e in page.events:
            print(f"  {e.event_id}  type={e.event_type}  hash={e.payload_hash[:16]}...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
