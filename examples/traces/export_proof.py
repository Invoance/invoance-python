"""Export the proof bundle for a sealed trace.

Usage
-----
    python examples/traces/export_proof.py <trace_id>

Example
-------
    python examples/traces/export_proof.py tr_a1b2c3d4e5f6
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    trace_id = sys.argv[1] if len(sys.argv) > 1 else os.getenv("TRACE_ID")

    if not trace_id:
        print("Usage: python export_proof.py <trace_id>")
        print("       Or set TRACE_ID environment variable")
        sys.exit(1)

    async with InvoanceClient() as client:
        proof = await client.traces.proof(trace_id)

        print(f"version:         {proof.version}")
        print(f"trace_id:        {proof.trace_id}")
        print(f"label:           {proof.label}")
        print(f"status:          {proof.status}")
        print(f"event_count:     {proof.event_count}")
        print(f"created_at:      {proof.created_at}")
        print(f"sealed_at:       {proof.sealed_at}")
        print(f"composite_hash:  {proof.composite_hash[:32]}...")
        print(f"tenant_domain:   {proof.tenant_domain}")

        # Save the proof bundle as JSON
        filename = f"proof_{proof.trace_id}.json"
        with open(filename, "w") as f:
            json.dump(proof.model_dump(), f, indent=2)
        print(f"\nProof bundle saved to: {filename}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
