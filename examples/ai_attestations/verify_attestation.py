"""Verify an AI attestation — by hash, raw JSON string, and dict.

Usage
-----
    python examples/ai_attestations/verify_attestation.py <attestation_id> <content_hash>

Example
-------
    python examples/ai_attestations/verify_attestation.py \
        fa5a24ab-ee48-4bc3-9e0f-158567ad6a0c \
        3d0671ab6c4939f4822716aa6062eb27fbbb5f9caaf40d784bcaedff6762abb7
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


def print_result(label: str, result):
    print(f"\n── {label} ──")
    print(f"  attestation_id: {result.attestation_id}")
    print(f"  match_result:   {result.match_result}")
    print(f"  matched_field:  {result.matched_field}")
    print(f"  anchored_hash:  {result.anchored_hash}")
    print(f"  submitted_hash: {result.submitted_hash}")
    print(f"  anchored_at:    {result.anchored_at}")

    org = result.organization
    if org:
        print(f"\n── Issuer ──")
        print(f"  name:            {org.name}")
        print(f"  issuer_name:     {org.issuer_name}")
        print(f"  domain:          {org.primary_domain}")
        print(f"  domain_verified: {org.domain_verified}")


async def main():
    if len(sys.argv) < 3:
        print("Usage: python verify_attestation.py <attestation_id> <content_hash>")
        sys.exit(1)

    attestation_id = sys.argv[1]
    content_hash = sys.argv[2]

    async with InvoanceClient() as client:
        result = await client.attestations.verify(
            attestation_id,
            content_hash=content_hash,
        )
        print_result("Verify by hash", result)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
