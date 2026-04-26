"""Events resource – ``client.events.*``"""

from __future__ import annotations

from typing import Any

from invoance._internal.http import HttpTransport
from invoance._internal.validate import assert_sha256_hex
from invoance.errors import ValidationError
from invoance.models import (
    ComplianceEvent,
    IngestEventResponse,
    ListEventsResponse,
    VerifyEventResponse,
)


class EventsResource:
    """Namespace for ``/events`` endpoints."""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    # ── POST /events ──────────────────────────────────────

    async def ingest(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        event_time: str | None = None,
        idempotency_key: str | None = None,
        trace_id: str | None = None,
    ) -> IngestEventResponse:
        """Ingest a compliance event.

        Parameters
        ----------
        event_type:
            Free-form event classifier (max 128 chars).
        payload:
            Arbitrary JSON payload to anchor. Max 64 KB.
        event_time:
            Optional ISO-8601 timestamp. Defaults to server ``now()``.
        idempotency_key:
            Optional idempotency header for safe retries.
        trace_id:
            Optional trace ID to associate the event with a trace.
        """
        body: dict[str, Any] = {
            "event_type": event_type,
            "payload": payload,
        }
        if event_time:
            body["event_time"] = event_time
        if trace_id:
            body["trace_id"] = trace_id

        raw = await self._t.post(
            "/events",
            json=body,
            idempotency_key=idempotency_key,
        )
        return IngestEventResponse.model_validate(raw)

    # ── GET /events ───────────────────────────────────────

    async def list(
        self,
        *,
        page: int = 1,
        limit: int = 50,
        date_from: str | None = None,
        date_to: str | None = None,
        event_type: str | None = None,
    ) -> ListEventsResponse:
        """Paginated event listing (max 500 per page, cached 30 s)."""
        raw = await self._t.get(
            "/events",
            params={
                "page": page,
                "limit": limit,
                "date_from": date_from,
                "date_to": date_to,
                "event_type": event_type,
            },
        )
        return ListEventsResponse.model_validate(raw)

    # ── GET /events/:event_id ─────────────────────────────

    async def get(self, event_id: str) -> ComplianceEvent:
        """Retrieve a single event by ID."""
        raw = await self._t.get(f"/events/{event_id}")
        return ComplianceEvent.model_validate(raw)

    # ── POST /events/:event_id/verify ─────────────────────

    async def verify(
        self,
        event_id: str,
        *,
        payload_hash: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> VerifyEventResponse:
        """Compare a hash against the anchored event hashes.

        Provide **either** ``payload_hash`` (hex SHA-256) **or** ``payload``
        (raw JSON — the server canonicalizes and hashes for you).
        Passing neither raises :class:`invoance.ValidationError`.
        """
        if payload_hash is None and payload is None:
            raise ValidationError(
                "events.verify requires either `payload_hash` or `payload`"
            )

        body: dict[str, Any] = {}
        if payload_hash is not None:
            assert_sha256_hex("payload_hash", payload_hash)
            body["payload_hash"] = payload_hash
        if payload is not None:
            body["payload"] = payload

        raw = await self._t.post(f"/events/{event_id}/verify", json=body)
        return VerifyEventResponse.model_validate(raw)
