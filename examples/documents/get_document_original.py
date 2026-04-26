"""Download the original file for an anchored document.

Usage
-----
    python examples/documents/get_document_original.py <event_id>
    python examples/documents/get_document_original.py <event_id> --out ./custom_name.pdf
"""

import argparse
import asyncio
import os

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


def parse_args():
    p = argparse.ArgumentParser(description="Download original anchored document")
    p.add_argument("event_id", help="Event ID of the anchored document")
    p.add_argument("--out", default=None, help="Override output filename")
    return p.parse_args()


async def main():
    args = parse_args()

    async with InvoanceClient() as client:
        # Fetch metadata to get the original filename
        doc = await client.documents.get(args.event_id)
        data = await client.documents.get_original(args.event_id)

        # Determine output filename
        if args.out:
            out_path = args.out
        else:
            # Use document_ref as filename, fall back to event_id
            ref = doc.document_ref or args.event_id
            out_path = os.path.basename(ref)

        with open(out_path, "wb") as f:
            f.write(data)

        print(f"Saved {len(data):,} bytes to {out_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
