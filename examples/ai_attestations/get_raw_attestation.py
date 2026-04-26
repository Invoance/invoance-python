"""Fetch the raw canonical JSON payload of an AI attestation.

Usage
-----
    python examples/ai_attestations/get_raw_attestation.py <attestation_id>
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
        print("Usage: python get_raw_attestation.py <attestation_id>")
        sys.exit(1)

    attestation_id = sys.argv[1]

    async with InvoanceClient() as client:
        raw = await client.attestations.get_raw(attestation_id)
        print(json.dumps(raw, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
