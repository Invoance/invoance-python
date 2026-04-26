"""Verify the Ed25519 signature of an AI attestation — fully client-side.

This proves that no field has been tampered with since ingestion,
including the timestamp, hashes, and all metadata. No trust in
the server is required.

Usage
-----
    pip install PyNaCl
    python examples/ai_attestations/verify_signature.py <attestation_id>
"""

import asyncio
import json
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_signature.py <attestation_id>")
        sys.exit(1)

    attestation_id = sys.argv[1]

    async with InvoanceClient() as client:
        result = await client.attestations.verify_signature(attestation_id)

        print(f"valid:          {result.valid}")
        print(f"reason:         {result.reason}")
        print(f"attestation_id: {result.attestation.attestation_id}")
        print(f"signature_alg:  {result.attestation.signature_alg}")

        if result.signed_data:
            print(f"\n── Signed data (tamper-proof fields) ──")
            print(json.dumps(result.signed_data, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
