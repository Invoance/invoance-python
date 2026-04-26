"""Verify a document — compare a hash against the anchored record.

Accepts either a file path (auto-hashes it) or a pre-computed hash.

Usage
-----
    python examples/documents/verify_document.py <event_id> <file_or_hash>

Examples
--------
    # Verify by pointing to the original file (auto-computes SHA-256)
    python examples/documents/verify_document.py 82d3ea4a-... ./invoice.pdf

    # Verify by pre-computed hash
    python examples/documents/verify_document.py 82d3ea4a-... a94a8fe5ccb19ba6...
"""

import asyncio
import hashlib
import os
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


def resolve_hash(value: str) -> str:
    """If value is a file path, compute SHA-256. Otherwise treat as hex hash."""
    if os.path.isfile(value):
        content = open(value, "rb").read()
        h = hashlib.sha256(content).hexdigest()
        print(f"File:   {os.path.basename(value)} ({len(content):,} bytes)")
        print(f"SHA256: {h}\n")
        return h
    return value


async def main():
    if len(sys.argv) < 3:
        print("Usage: python verify_document.py <event_id> <file_or_hash>\n")
        print("Examples:")
        print("  python verify_document.py 82d3ea4a-... ./invoice.pdf")
        print("  python verify_document.py 82d3ea4a-... a94a8fe5ccb19ba6...")
        sys.exit(1)

    event_id = sys.argv[1]
    document_hash = resolve_hash(sys.argv[2])

    async with InvoanceClient() as client:
        result = await client.documents.verify(
            event_id,
            document_hash=document_hash,
        )
        print(f"event_id:       {result.event_id}")
        print(f"match_result:   {result.match_result}")
        print(f"document_ref:   {result.document_ref}")
        print(f"anchored_hash:  {result.anchored_hash}")
        print(f"submitted_hash: {result.submitted_hash}")
        print(f"anchored_at:    {result.anchored_at}")

        org = result.organization
        if org:
            print(f"\n── Issuer ──")
            print(f"  name:            {org.name}")
            print(f"  issuer_name:     {org.issuer_name}")
            print(f"  domain:          {org.primary_domain}")
            print(f"  domain_verified: {org.domain_verified}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
