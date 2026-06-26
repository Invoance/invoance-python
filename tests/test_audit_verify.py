"""Client-side audit verify — golden-vector conformance + tamper test.

Reproduces the backend's frozen canonical bytes / payload hash for every committed
vector, confirms the committed signature verifies, and that a tampered field fails.
"""

from __future__ import annotations

import json
import os

from invoance import verify_audit_event
from invoance._internal.audit_canonical import canonical_audit_bytes, payload_hash_hex

HERE = os.path.dirname(os.path.abspath(__file__))
VECTORS = os.path.join(HERE, "fixtures", "audit_vectors.json")


def _load() -> dict:
    with open(VECTORS, encoding="utf-8") as f:
        return json.load(f)


def _api_event(vec: dict) -> dict:
    """Reshape a vector's signed input into an API-style event object."""
    ev = dict(vec["event"])
    ev["id"] = ev.pop("event_id")
    ev["signature"] = vec["signature_ed25519"]
    ev["payload_hash"] = vec["payload_hash_sha256"]
    ev["signing_public_key"] = vec["public_key"]
    return ev


def test_golden_canonical_bytes_and_hash() -> None:
    doc = _load()
    assert doc["schema_id"] == "invoance.audit/1"
    for v in doc["vectors"]:
        canonical = canonical_audit_bytes(v["event"])
        assert canonical.decode("utf-8") == v["canonical_utf8"], v["name"]
        assert payload_hash_hex(canonical) == v["payload_hash_sha256"], v["name"]


def test_golden_signatures_verify_under_embedded_key() -> None:
    doc = _load()
    for v in doc["vectors"]:
        r = verify_audit_event(_api_event(v))
        assert r.valid, f"{v['name']}: {r.reason}"
        assert r.key_source == "event"


def test_pinned_key_and_tamper() -> None:
    doc = _load()
    ev = _api_event(doc["vectors"][0])

    pinned = verify_audit_event(ev, public_key=doc["test_public_key"])
    assert pinned.valid and pinned.key_source == "pinned"

    tampered = dict(ev)
    tampered["action"] = ev["action"] + ".tampered"
    bad = verify_audit_event(tampered)
    assert not bad.valid
    assert bad.reason == "payload_hash_mismatch"
