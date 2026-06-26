"""Audit Logs: create an async export and poll until the download URL is ready.

Usage
-----
    python examples/audit/export.py <organization_id> [csv|ndjson]
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python examples/audit/export.py <organization_id> [csv|ndjson]")
        sys.exit(1)
    organization_id = sys.argv[1]
    fmt = sys.argv[2] if len(sys.argv) > 2 else "csv"

    async with InvoanceClient() as client:
        job = await client.audit.exports.create(organization_id=organization_id, format=fmt)
        export_id = job["id"]
        print(f"queued export {export_id} ({fmt})")

        status = job
        for _ in range(30):
            status = await client.audit.exports.get(export_id)
            if status["status"] in ("ready", "failed"):
                break
            await asyncio.sleep(2)

        print(f"status: {status['status']} rows={status.get('row_count')} error={status.get('error')}")
        if status.get("download_url"):
            print(f"download: {status['download_url']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
