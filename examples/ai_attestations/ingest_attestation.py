"""Ingest an AI attestation — anchor an AI input/output pair.

Usage
-----
    python examples/ai_attestations/ingest_attestation.py
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    async with InvoanceClient() as client:
        result = await client.attestations.ingest(
            attestation_type="output",
            input="Summarize Q1 2026 revenue figures.",
            output="Q1 2026 revenue was $12.4M, up 18% year-over-year.",
            model_provider="openai",
            model_name="gpt-4.1",
            model_version="2026-04-14",
            subject={
                "user_id": "user_7b1c",
                "session_id": "sess_4f9a",
                # Custom fields — any key-value pairs your org needs
                "department": "finance",
                "request_id": "req_a8c3e1",
            },
        )
        print(f"attestation_id: {result.attestation_id}")
        print(f"created_at:     {result.created_at}")
        print(f"payload_hash:   {result.payload_hash}")
        print(f"input_hash:     {result.input_hash}")
        print(f"output_hash:    {result.output_hash}")
        print(f"status:         {result.status}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
