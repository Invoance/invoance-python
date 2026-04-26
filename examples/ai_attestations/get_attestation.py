"""Fetch a single AI attestation by ID and print it.

Usage
-----
    python examples/ai_attestations/get_attestation.py <attestation_id>
"""

import asyncio
import sys

from dotenv import load_dotenv
from invoance import InvoanceClient
from invoance.errors import InvoanceError

load_dotenv()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python get_attestation.py <attestation_id>")
        sys.exit(1)

    attestation_id = sys.argv[1]

    async with InvoanceClient() as client:
        att = await client.attestations.get(attestation_id)
        print(f"attestation_id:   {att.attestation_id}")
        print(f"tenant_id:        {att.tenant_id}")
        print(f"type:             {att.attestation_type}")
        print(f"attestation_hash: {att.attestation_hash}")
        print(f"input_hash:       {att.input_hash}")
        print(f"output_hash:      {att.output_hash}")
        print(f"signature:        {att.signature[:40]}...")
        print(f"public_key:       {att.public_key[:40]}...")
        print(f"signature_alg:    {att.signature_alg}")
        print(f"model_provider:   {att.model_provider}")
        print(f"model_name:       {att.model_name}")
        print(f"model_version:    {att.model_version}")
        print(f"retention_policy: {att.retention_policy}")
        print(f"created_at:       {att.created_at}")

        if att.organization:
            org = att.organization
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
