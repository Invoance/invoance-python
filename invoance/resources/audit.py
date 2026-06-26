"""Audit Logs resource — ``client.audit.*``

The audit-log product surface: an append-only, per-tenant signed event ledger with
end-customer orgs, SIEM/webhook streams, hosted-viewer portal links, and async exports.

Methods return the server's JSON as plain ``dict`` objects (the audit surface is broad
and still evolving; typed models may follow). Errors are raised as
:class:`invoance.InvoanceError` subclasses, same as the rest of the SDK. For an offline
signature check of a returned event, see :func:`invoance.verify_audit_event`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from invoance._internal.http import HttpTransport


def content_idempotency_key(body: dict[str, Any]) -> str:
    """Derive a stable ``Idempotency-Key`` from an event body.

    Hashing the request content means a retried call with identical content reuses the
    same key (so the server dedupes it), while genuinely different events get distinct
    keys. Pass the same ``body`` fields you hand to :meth:`AuditEventsResource.ingest`.
    """
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "idem_" + hashlib.sha256(canonical).hexdigest()


def _now_rfc3339() -> str:
    """Current UTC time as RFC3339 (ms + Z), the audit canonical timestamp form."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class AuditEventsResource:
    """``client.audit.events.*`` — the signed event ledger."""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    async def ingest(
        self,
        *,
        org: str,
        action: str,
        actor: dict[str, Any],
        occurred_at: str | None = None,
        targets: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Append one audit event (POST /audit/events).

        ``org`` is your external org id; ``actor`` is ``{"type","id","name"?}``.
        ``occurred_at`` defaults to now (RFC3339, ms + Z). The ledger REQUIRES an
        Idempotency-Key, so one is derived from the event content when ``idempotency_key``
        is omitted (override it with a stable value for safe retries).
        """
        body: dict[str, Any] = {
            "org": org,
            "action": action,
            "occurred_at": occurred_at or _now_rfc3339(),
            "actor": actor,
            "targets": targets if targets is not None else [],
        }
        if context is not None:
            body["context"] = context
        if metadata is not None:
            body["metadata"] = metadata
        idem = idempotency_key or content_idempotency_key(body)
        return await self._t.post("/audit/events", json=body, idempotency_key=idem)

    async def list(
        self,
        *,
        org_id: str | None = None,
        actions: str | None = None,
        actor_id: str | None = None,
        target_id: str | None = None,
        occurred_after: str | None = None,
        occurred_before: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """List events (GET /audit/events), keyset-paginated via ``cursor``."""
        return await self._t.get(
            "/audit/events",
            params={
                "org_id": org_id,
                "actions": actions,
                "actor_id": actor_id,
                "target_id": target_id,
                "occurred_after": occurred_after,
                "occurred_before": occurred_before,
                "limit": limit,
                "cursor": cursor,
            },
        )

    async def get(self, event_id: str) -> dict[str, Any]:
        """Fetch one event (GET /audit/events/{id})."""
        return await self._t.get(f"/audit/events/{event_id}")

    async def verify(self, event_id: str) -> dict[str, Any]:
        """Server-side verify of a stored event's signature (GET /audit/events/{id}/verify).

        For an offline, client-side check use :func:`invoance.verify_audit_event`.
        """
        return await self._t.get(f"/audit/events/{event_id}/verify")


class AuditOrgsResource:
    """``client.audit.orgs.*`` — end-customer orgs."""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    async def create(self, *, external_id: str, name: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"external_id": external_id}
        if name is not None:
            body["name"] = name
        return await self._t.post("/audit/orgs", json=body)

    async def list(self) -> dict[str, Any]:
        return await self._t.get("/audit/orgs")

    async def integrity(self, org_id: str) -> dict[str, Any]:
        """Seq-gap integrity scan for an org (GET /audit/orgs/{id}/integrity)."""
        return await self._t.get(f"/audit/orgs/{org_id}/integrity")

    async def set_retention(self, org_id: str, *, days: int) -> dict[str, Any]:
        """Set retention in days (clamped to the plan cap)."""
        return await self._t.put(f"/audit/orgs/{org_id}/retention", json={"days": days})


class AuditStreamsResource:
    """``client.audit.streams.*`` — SIEM/webhook destinations."""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    async def create(self, org_id: str, *, url: str, type: str = "webhook") -> dict[str, Any]:
        """Create a stream; the signing secret is returned ONCE in the response."""
        return await self._t.post(f"/audit/orgs/{org_id}/streams", json={"type": type, "url": url})

    async def list(self, org_id: str) -> dict[str, Any]:
        return await self._t.get(f"/audit/orgs/{org_id}/streams")

    async def delete(self, org_id: str, stream_id: str) -> dict[str, Any]:
        return await self._t.delete(f"/audit/orgs/{org_id}/streams/{stream_id}")

    async def test(self, org_id: str, stream_id: str) -> dict[str, Any]:
        """Send a synthetic delivery to verify the destination."""
        return await self._t.post(f"/audit/orgs/{org_id}/streams/{stream_id}/test")


class AuditPortalSessionsResource:
    """``client.audit.portal_sessions.*`` — hosted-viewer one-time links."""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    async def create(
        self,
        *,
        org_id: str,
        intent: str,
        session_duration_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Mint a one-time portal link. ``intent`` is ``audit_logs`` or ``log_streams``."""
        body: dict[str, Any] = {"org_id": org_id, "intent": intent}
        if session_duration_seconds is not None:
            body["session_duration_seconds"] = session_duration_seconds
        return await self._t.post("/audit/portal_sessions", json=body)


class AuditExportsResource:
    """``client.audit.exports.*`` — async CSV/NDJSON exports."""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    async def create(
        self,
        *,
        org_id: str,
        format: str,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Queue an export job. ``format`` is ``csv`` or ``ndjson``."""
        body: dict[str, Any] = {"org_id": org_id, "format": format}
        if filters is not None:
            body["filters"] = filters
        return await self._t.post("/audit/exports", json=body)

    async def get(self, export_id: str) -> dict[str, Any]:
        """Poll an export; when ``status == 'ready'`` the response has ``download_url``."""
        return await self._t.get(f"/audit/exports/{export_id}")


class AuditResource:
    """``client.audit`` — namespace bundling the audit-log sub-resources."""

    def __init__(self, transport: HttpTransport) -> None:
        self.events = AuditEventsResource(transport)
        self.orgs = AuditOrgsResource(transport)
        self.streams = AuditStreamsResource(transport)
        self.portal_sessions = AuditPortalSessionsResource(transport)
        self.exports = AuditExportsResource(transport)
