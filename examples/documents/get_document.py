"""Retrieve a single document event by ID.

Usage
-----
    python examples/documents/get_document.py <event_id>
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python get_document.py <event_id>")
        sys.exit(1)

    event_id = sys.argv[1]

    async with InvoanceClient() as client:
        doc = await client.documents.get(event_id)
        print(f"event_id:       {doc.event_id}")
        print(f"document_ref:   {doc.document_ref}")
        print(f"document_hash:  {doc.document_hash}")
        print(f"has_original:   {doc.has_original}")
        print(f"created_at:     {doc.created_at}")
        print(f"metadata:       {doc.metadata}")

        if doc.organization:
            org = doc.organization
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
