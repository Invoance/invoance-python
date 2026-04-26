"""Anchor a document in the immutable ledger.

Uses ``anchor_file()`` — the SDK reads the file, computes the SHA-256
hash, and uploads the original bytes automatically.

Usage
-----
    python examples/documents/anchor_document.py <file_path>
    python examples/documents/anchor_document.py <file_path> --ref "Invoice #1042"
    python examples/documents/anchor_document.py <file_path> --ref "Contract v2" --type contract
    python examples/documents/anchor_document.py <file_path> --metadata '{"amount": 5230, "currency": "USD"}'

Example
-------
    python examples/documents/anchor_document.py ./invoice.pdf --ref "Invoice #1042" \
        --metadata '{"amount": 5230, "currency": "USD"}'
"""

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import ConflictError, InvoanceError

load_dotenv()


def parse_args():
    p = argparse.ArgumentParser(description="Anchor a document in the immutable ledger")
    p.add_argument("file", help="Path to the file to anchor")
    p.add_argument("--ref", default=None, help="Human-readable document reference (e.g. 'Invoice #1042')")
    p.add_argument("--type", dest="event_type", default=None, help="Event type (e.g. invoice, contract)")
    p.add_argument("--metadata", default=None, help="JSON metadata (e.g. '{\"amount\": 5230}')")
    p.add_argument("--no-upload", action="store_true", help="Skip uploading original bytes")
    return p.parse_args()


async def main():
    args = parse_args()

    file_path = os.path.abspath(args.file)
    if not os.path.isfile(file_path):
        print(f"Error: file not found: {file_path}")
        sys.exit(1)

    metadata = None
    if args.metadata:
        try:
            metadata = json.loads(args.metadata)
        except json.JSONDecodeError as e:
            print(f"Error: invalid --metadata JSON: {e}")
            sys.exit(1)

    async with InvoanceClient() as client:
        try:
            result = await client.documents.anchor_file(
                file=file_path,
                document_ref=args.ref,
                event_type=args.event_type,
                metadata=metadata,
                skip_original=args.no_upload,
            )
        except ConflictError as e:
            print(f"Already anchored: {e}")
            sys.exit(0)

        print(f"event_id:      {result.event_id}")
        print(f"document_hash: {result.document_hash}")
        print(f"status:        {result.status}")
        print(f"created_at:    {result.created_at}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
