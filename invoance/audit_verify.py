"""Offline, client-side signature verification for audit events.

Reconstructs the canonical signed bytes from an event returned by the API and checks the
Ed25519 signature with PyNaCl, with no network call.

Trust note: by default this verifies against the key embedded in the event
(``event["signing_public_key"]``), which proves the payload is internally consistent
with that key. But an attacker with row-write access could re-sign a tampered event
under their OWN keypair and swap the embedded key too, and that would still pass. For a
real tamper guarantee, pass ``public_key`` = the tenant's registered key (the server
pins it from ``tenant_keys`` and never trusts the row's key).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Union

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from invoance._internal.audit_canonical import canonical_audit_bytes, payload_hash_hex


@dataclass(frozen=True)
class AuditVerifyResult:
    """Outcome of :func:`verify_audit_event`."""

    valid: bool
    reason: Optional[str]
    payload_hash: str
    key_source: str  # "pinned" (you supplied the key) | "event" (the embedded key)


def _to_key_bytes(k: Union[str, bytes]) -> bytes:
    return bytes(k) if isinstance(k, (bytes, bytearray)) else bytes.fromhex(k)


def verify_audit_event(
    event: dict[str, Any],
    *,
    public_key: Optional[Union[str, bytes]] = None,
) -> AuditVerifyResult:
    """Verify one audit event's signature offline.

    ``event`` is the object returned by ``client.audit.events.get(...)``. Pass
    ``public_key`` (hex string or 32 raw bytes) to pin the tenant's known key; see the
    module docstring on why that matters for a real tamper guarantee.
    """
    key_source = "pinned" if public_key is not None else "event"

    signed_input: dict[str, Any] = {
        "org_id": event.get("org_id"),
        "event_id": event.get("id", event.get("event_id")),
        "seq": event.get("seq"),
        "ingested_at": event.get("ingested_at"),
        "action": event.get("action"),
        "occurred_at": event.get("occurred_at"),
        "actor": event.get("actor"),
        "targets": event.get("targets"),
    }
    if event.get("context") is not None:
        signed_input["context"] = event["context"]
    if event.get("metadata") is not None:
        signed_input["metadata"] = event["metadata"]

    try:
        canonical = canonical_audit_bytes(signed_input)
    except Exception:
        return AuditVerifyResult(False, "canonicalization_failed", "", key_source)

    recomputed = payload_hash_hex(canonical)
    stored_hash = event.get("payload_hash")
    if stored_hash is not None and stored_hash != recomputed:
        return AuditVerifyResult(False, "payload_hash_mismatch", recomputed, key_source)

    key = public_key if public_key is not None else event.get("signing_public_key")
    if not key:
        return AuditVerifyResult(False, "no_public_key", recomputed, key_source)

    sig = event.get("signature")
    if not sig:
        return AuditVerifyResult(False, "no_signature", recomputed, key_source)

    try:
        sig_bytes = bytes.fromhex(sig) if isinstance(sig, str) else bytes(sig)
        VerifyKey(_to_key_bytes(key)).verify(canonical, sig_bytes)
    except (BadSignatureError, ValueError, TypeError):
        return AuditVerifyResult(False, "signature_invalid", recomputed, key_source)

    return AuditVerifyResult(True, None, recomputed, key_source)
