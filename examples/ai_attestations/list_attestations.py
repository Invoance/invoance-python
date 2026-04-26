"""Paginated attestation listing with optional filters.

Usage
-----
    python examples/ai_attestations/list_attestations.py
    python examples/ai_attestations/list_attestations.py --limit 5
    python examples/ai_attestations/list_attestations.py --attestation-type output --model-provider openai
    python examples/ai_attestations/list_attestations.py --date-from 2025-01-01 --date-to 2025-12-31
"""

import argparse
import asyncio

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


def parse_args():
    p = argparse.ArgumentParser(description="List AI attestations")
    p.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    p.add_argument("--limit", type=int, default=10, help="Results per page (default: 10)")
    p.add_argument("--attestation-type", default=None, help="Filter by type (e.g. output, input)")
    p.add_argument("--model-provider", default=None, help="Filter by model provider (e.g. openai)")
    p.add_argument("--date-from", default=None, help="Start date filter (YYYY-MM-DD)")
    p.add_argument("--date-to", default=None, help="End date filter (YYYY-MM-DD)")
    return p.parse_args()


async def main():
    args = parse_args()

    async with InvoanceClient() as client:
        page = await client.attestations.list(
            page=args.page,
            limit=args.limit,
            attestation_type=args.attestation_type,
            model_provider=args.model_provider,
            date_from=args.date_from,
            date_to=args.date_to,
        )
        print(f"Total attestations: {page.total}")
        print(f"Page {page.page}, has_more: {page.has_more}\n")

        for a in page.attestations:
            print(
                f"  {a.attestation_id}  type={a.attestation_type}"
                f"  model={a.model_provider}/{a.model_name}"
            )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvoanceError as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        sys.exit(1)
