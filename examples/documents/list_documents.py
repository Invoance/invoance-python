"""Paginated document listing with optional filters.

Usage
-----
    python examples/documents/list_documents.py
    python examples/documents/list_documents.py --limit 5
    python examples/documents/list_documents.py --limit 20 --page 2 --document-ref invoice-2025-001
    python examples/documents/list_documents.py --date-from 2025-01-01 --date-to 2025-12-31
"""

import argparse
import asyncio

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


def parse_args():
    p = argparse.ArgumentParser(description="List anchored documents")
    p.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    p.add_argument("--limit", type=int, default=10, help="Results per page (default: 10)")
    p.add_argument("--document-ref", default=None, help="Filter by document reference")
    p.add_argument("--date-from", default=None, help="Start date filter (YYYY-MM-DD)")
    p.add_argument("--date-to", default=None, help="End date filter (YYYY-MM-DD)")
    return p.parse_args()


async def main():
    args = parse_args()

    async with InvoanceClient() as client:
        page = await client.documents.list(
            page=args.page,
            limit=args.limit,
            document_ref=args.document_ref,
            date_from=args.date_from,
            date_to=args.date_to,
        )
        print(f"Total documents: {page.total}")
        print(f"Page {page.page}, has_more: {page.has_more}\n")

        for d in page.documents:
            print(f"  {d.event_id}  ref={d.document_ref}  hash={d.document_hash[:16]}...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
