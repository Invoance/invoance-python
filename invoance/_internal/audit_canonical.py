"""``invoance.audit/1`` canonical serializer (client-side).

Reproduces the server's frozen canonicalization (``product/audit-log/spec-audit-1.md``
§4) so an event's signature can be checked offline. Conformance is pinned by the same
golden vectors the backend uses (``tests/fixtures/audit_vectors.json``).

Canonical bytes = build the signed object (the signed fields that are present and
non-null, both timestamps normalized, plus a forced ``schema_id``), strip null members
recursively, sort every object's keys, emit compact UTF-8. That is exactly
``json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)``.

Once the spec is frozen this behavior is PERMANENT: any change after the first real
event is signed breaks verification for every prior event.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

SCHEMA_ID = "invoance.audit/1"

# §4.3 fields included in the signed object, besides the forced schema_id.
SIGNED_FIELDS = (
    "org_id",
    "event_id",
    "seq",
    "ingested_at",
    "action",
    "occurred_at",
    "actor",
    "targets",
    "context",
    "metadata",
)
REQUIRED_FIELDS = (
    "org_id",
    "event_id",
    "seq",
    "ingested_at",
    "action",
    "occurred_at",
    "actor",
    "targets",
)

_RFC3339 = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(Z|z|[+-]\d{2}:\d{2})$"
)


def normalize_ts(value: str) -> str:
    """RFC3339 -> the one canonical form (§4.4): UTC, exactly 3 fractional digits
    (truncated, not rounded), trailing ``Z``."""
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    m = _RFC3339.match(value.strip())
    if not m:
        raise ValueError(f"invalid RFC3339 timestamp: {value!r}")
    yr, mo, dy, hh, mi, ss, frac, off = m.groups()
    millis = int(((frac or "") + "000")[:3])  # truncate to milliseconds
    dt = datetime(
        int(yr), int(mo), int(dy), int(hh), int(mi), int(ss), millis * 1000, tzinfo=timezone.utc
    )
    if off not in ("Z", "z"):
        sign = 1 if off[0] == "+" else -1
        dt = dt - timedelta(hours=sign * int(off[1:3]), minutes=sign * int(off[4:6]))
    return (
        f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
        f"T{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}.{dt.microsecond // 1000:03d}Z"
    )


def _strip_nulls(v: Any) -> Any:
    """§4.2 r5: remove null object members recursively (null == absent)."""
    if isinstance(v, dict):
        return {k: _strip_nulls(val) for k, val in v.items() if val is not None}
    if isinstance(v, list):
        return [_strip_nulls(x) for x in v]
    return v


def build_signed_object(event: dict[str, Any]) -> dict[str, Any]:
    """§4.3: keep the present, non-null signed fields, normalize timestamps, force
    ``schema_id``. ``version`` / ``org`` / envelope columns are dropped by construction."""
    if not isinstance(event, dict):
        raise ValueError("event must be a JSON object")
    for f in REQUIRED_FIELDS:
        if event.get(f) is None:
            raise ValueError(f"missing required field: {f}")
    out: dict[str, Any] = {}
    for f in SIGNED_FIELDS:
        v = event.get(f)
        if v is None:
            continue
        out[f] = normalize_ts(v) if f in ("occurred_at", "ingested_at") else v
    out["schema_id"] = SCHEMA_ID
    return out


def canonical_audit_bytes(event: dict[str, Any]) -> bytes:
    """The canonical signed bytes for an audit event (§4.1-§4.2)."""
    signed = _strip_nulls(build_signed_object(event))
    return json.dumps(signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def payload_hash_hex(canonical: bytes) -> str:
    """§4.5: ``payload_hash = SHA-256(canonical bytes)``, lowercase hex."""
    return hashlib.sha256(canonical).hexdigest()
