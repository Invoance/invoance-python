"""AI Attestations resource – ``client.attestations.*``"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from invoance._internal.http import HttpTransport
from invoance._internal.validate import assert_sha256_hex
from invoance.models import (
    AiAttestation,
    IngestAttestationResponse,
    ListAttestationsResponse,
    VerifyAttestationResponse,
)


class AttestationsResource:
    """Namespace for ``/ai/attestations`` endpoints."""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    # ── POST /ai/attestations ─────────────────────────────

    async def ingest(
        self,
        *,
        attestation_type: str,
        input: str,
        output: str,
        model_provider: str,
        model_name: str,
        model_version: str,
        subject: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        trace_id: str | None = None,
    ) -> IngestAttestationResponse:
        """Anchor an AI attestation.

        Parameters
        ----------
        attestation_type:
            Attestation type: ``"output"``, ``"decision"``, or ``"approval"``.
            Serialised on the wire as the ``type`` field.
        input:
            The prompt / input text.
        output:
            The model's response / output text.
        model_provider:
            E.g. ``"openai"``, ``"anthropic"``.
        model_name:
            E.g. ``"gpt-4o"``, ``"claude-sonnet-4-20250514"``.
        model_version:
            Semver or date string of the model.
        subject:
            Optional subject context — who/what triggered the attestation.
            Well-known keys: ``user_id``, ``session_id``. Any additional
            keys are accepted as custom tenant-specific context (e.g.
            ``department``, ``request_id``, ``trace_id``). All fields
            become part of the attestation hash.
        idempotency_key:
            Idempotency header for safe retries.
        """
        body: dict[str, Any] = {
            "type": attestation_type,
            "payload": {
                "input": input,
                "output": output,
            },
            "context": {
                "model_provider": model_provider,
                "model_name": model_name,
                "model_version": model_version,
            },
        }
        if subject:
            body["subject"] = subject
        if trace_id is not None:
            body["trace_id"] = trace_id

        raw = await self._t.post(
            "/ai/attestations",
            json=body,
            idempotency_key=idempotency_key,
        )
        return IngestAttestationResponse.model_validate(raw)

    # ── GET /ai/attestations ──────────────────────────────

    async def list(
        self,
        *,
        page: int = 1,
        limit: int = 50,
        date_from: str | None = None,
        date_to: str | None = None,
        attestation_type: str | None = None,
        model_provider: str | None = None,
    ) -> ListAttestationsResponse:
        """Paginated attestation listing (max 500 per page, cached 30 s)."""
        raw = await self._t.get(
            "/ai/attestations",
            params={
                "page": page,
                "limit": limit,
                "date_from": date_from,
                "date_to": date_to,
                "attestation_type": attestation_type,
                "model_provider": model_provider,
            },
        )
        return ListAttestationsResponse.model_validate(raw)

    # ── GET /ai/attestations/:attestation_id ──────────────

    async def get(self, attestation_id: str) -> AiAttestation:
        """Retrieve a single attestation by ID."""
        raw = await self._t.get(f"/ai/attestations/{attestation_id}")
        return AiAttestation.model_validate(raw)

    # ── GET /ai/attestations/:attestation_id/raw ──────────

    async def get_raw(self, attestation_id: str) -> dict[str, Any]:
        """Retrieve the original canonical JSON payload from R2.

        This is the exact request body that was hashed and signed
        at ingestion time. Cached server-side for 5 minutes.
        """
        raw = await self._t.get(f"/ai/attestations/{attestation_id}/raw")
        return raw

    # ── POST /ai/attestations/:attestation_id/verify ──────

    async def verify(
        self,
        attestation_id: str,
        *,
        content_hash: str,
    ) -> VerifyAttestationResponse:
        """Compare a hash against the anchored attestation hashes.

        Parameters
        ----------
        attestation_id:
            The attestation UUID.
        content_hash:
            Hex-encoded SHA-256 to verify (64 chars).
        """
        assert_sha256_hex("content_hash", content_hash)
        raw = await self._t.post(
            f"/ai/attestations/{attestation_id}/verify",
            json={"content_hash": content_hash},
        )
        return VerifyAttestationResponse.model_validate(raw)

    async def verify_payload(
        self,
        attestation_id: str,
        *,
        payload: "dict[str, Any] | str | bytes",
    ) -> VerifyAttestationResponse:
        """Verify by raw payload — hashes client-side, then calls verify.

        Accepts the canonical JSON stored in Invoance (the "Raw immutable
        record") as a ``str``, ``bytes``, or a ``dict``.

        When a ``dict`` is passed the keys **must** be in the same order
        as the Rust struct (``type``, ``payload``, ``context``,
        ``subject``) because the backend hashes using ``serde_json``
        which preserves struct field order — *not* alphabetical order.

        The safest approach is to pass the raw JSON string exactly as
        shown in the dashboard's "Raw immutable record" viewer.

        Parameters
        ----------
        attestation_id:
            The attestation UUID.
        payload:
            The original request body.  Accepted forms:

            * **str / bytes** — raw JSON (pretty-printed is fine;
              it will be compacted automatically).
            * **dict** — keys must follow Rust struct field order::

                  {
                      "type": "output",
                      "payload": {"input": "...", "output": "..."},
                      "context": {"model_provider": "...", ...},
                      "subject": null
                  }
        """
        if isinstance(payload, bytes):
            payload = payload.decode()

        if isinstance(payload, str):
            # Re-parse to compact form (strips pretty-print whitespace)
            # json.loads preserves key order from the source string
            payload = json.loads(payload)

        canonical = json.dumps(payload, separators=(",", ":"))
        content_hash = hashlib.sha256(canonical.encode()).hexdigest()
        return await self.verify(attestation_id, content_hash=content_hash)

    async def verify_signature(
        self,
        attestation_id: str,
    ) -> "SignatureVerificationResult":
        """Verify the Ed25519 signature of an attestation — fully client-side.

        Fetches the attestation, then verifies the cryptographic signature
        against the ``signed_payload`` using the ``public_key``.  This
        proves that **no field has been tampered with** since ingestion —
        including the timestamp, hashes, and metadata.

        No trust in the server is required: the verification happens
        entirely in the SDK using the public key.

        Returns
        -------
        SignatureVerificationResult
            Contains ``valid`` (bool), the attestation, and details.
        """
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError

        att = await self.get(attestation_id)

        signed_payload_bytes = bytes.fromhex(att.signed_payload)
        signature_bytes = bytes.fromhex(att.signature)
        public_key_bytes = bytes.fromhex(att.public_key)

        try:
            vk = VerifyKey(public_key_bytes)
            vk.verify(signed_payload_bytes, signature_bytes)
            valid = True
            reason = None
        except BadSignatureError:
            valid = False
            reason = "Signature does not match signed_payload + public_key"
        except Exception as exc:
            valid = False
            reason = str(exc)

        # Parse the signed payload to show what was covered
        try:
            signed_data = json.loads(signed_payload_bytes.decode())
        except Exception:
            signed_data = None

        return SignatureVerificationResult(
            valid=valid,
            reason=reason,
            attestation=att,
            signed_data=signed_data,
        )


class SignatureVerificationResult:
    """Result of client-side Ed25519 signature verification."""

    def __init__(
        self,
        *,
        valid: bool,
        reason: "str | None",
        attestation: "AiAttestation",
        signed_data: "dict | None",
    ):
        self.valid = valid
        self.reason = reason
        self.attestation = attestation
        self.signed_data = signed_data

    def __repr__(self) -> str:
        return f"SignatureVerificationResult(valid={self.valid}, reason={self.reason!r})"
