"""Export the proof bundle as a PDF for a sealed trace.

Usage
-----
    python examples/traces/export_proof_pdf.py <trace_id>

Example
-------
    python examples/traces/export_proof_pdf.py 6127bb48-bc6c-4cf6-8a2e-92ae6168203c
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    trace_id = sys.argv[1] if len(sys.argv) > 1 else os.getenv("TRACE_ID")

    if not trace_id:
        print("Usage: python export_proof_pdf.py <trace_id>")
        print("       Or set TRACE_ID environment variable")
        sys.exit(1)

    async with InvoanceClient() as client:
        pdf_bytes = await client.traces.proof_pdf(trace_id)

        filename = f"proof_{trace_id}.pdf"
        with open(filename, "wb") as f:
            f.write(pdf_bytes)

        print(f"PDF proof bundle saved to: {filename}")
        print(f"Size: {len(pdf_bytes):,} bytes")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
