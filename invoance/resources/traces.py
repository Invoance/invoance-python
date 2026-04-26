"""Traces resource – ``client.traces.*``"""

from __future__ import annotations

from typing import Any, Optional

from invoance._internal.http import HttpTransport
from invoance.models import (
    CreateTraceResponse,
    DeleteTraceResponse,
    ListTracesResponse,
    TraceDetail,
    SealTraceResponse,
    TraceProofBundle,
)


class TracesResource:
    """Namespace for ``/traces`` endpoints."""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    # ── POST /traces ───────────────────────────────────────

    async def create(
        self,
        *,
        label: str,
        metadata: dict[str, Any] | None = None,
    ) -> CreateTraceResponse:
        """Create a new trace.

        Parameters
        ----------
        label:
            Human-readable name for the trace (max 255 chars).
        metadata:
            Optional structured context (tenant-defined, opaque to Invoance).
        """
        body: dict[str, Any] = {"label": label}
        if metadata is not None:
            body["metadata"] = metadata

        raw = await self._t.post("/traces", json=body)
        return CreateTraceResponse.model_validate(raw)

    # ── GET /traces ────────────────────────────────────────

    async def list(
        self,
        *,
        page: int = 1,
        limit: int = 25,
        status: str | None = None,
    ) -> ListTracesResponse:
        """Paginated trace listing."""
        raw = await self._t.get(
            "/traces",
            params={
                "page": page,
                "limit": limit,
                "status": status,
            },
        )
        return ListTracesResponse.model_validate(raw)

    # ── GET /traces/:trace_id ──────────────────────────────

    async def get(
        self,
        trace_id: str,
        *,
        event_page: int = 1,
        event_limit: int = 50,
    ) -> TraceDetail:
        """Retrieve a single trace with paginated event summaries.

        Parameters
        ----------
        trace_id:
            UUID of the trace.
        event_page:
            Page number for events (1-based, default 1).
        event_limit:
            Max events per page (default 50, max 200).
        """
        raw = await self._t.get(
            f"/traces/{trace_id}",
            params={"event_page": event_page, "event_limit": event_limit},
        )
        return TraceDetail.model_validate(raw)

    # ── DELETE /traces/:trace_id ────────────────────────────

    async def delete(self, trace_id: str) -> DeleteTraceResponse:
        """Delete an empty open trace.

        Only traces with status ``open`` and zero events can be deleted.
        Traces that contain events should be sealed instead.
        """
        raw = await self._t.delete(f"/traces/{trace_id}")
        return DeleteTraceResponse.model_validate(raw)

    # ── POST /traces/:trace_id/seal ────────────────────────

    async def seal(self, trace_id: str) -> SealTraceResponse:
        """Seal a trace. Async — returns 202, seal happens in background."""
        raw = await self._t.post(f"/traces/{trace_id}/seal", json={})
        return SealTraceResponse.model_validate(raw)

    # ── GET /traces/:trace_id/proof ────────────────────────

    async def proof(self, trace_id: str) -> TraceProofBundle:
        """Export the proof bundle for a sealed trace (JSON)."""
        raw = await self._t.get(f"/traces/{trace_id}/proof")
        return TraceProofBundle.model_validate(raw)

    # ── GET /traces/:trace_id/proof/pdf ─────────────────

    async def proof_pdf(self, trace_id: str) -> bytes:
        """Download the proof bundle as a PDF for a sealed trace.

        Returns raw PDF bytes. Write to a file with:

            pdf = await client.traces.proof_pdf(trace_id)
            with open("proof.pdf", "wb") as f:
                f.write(pdf)
        """
        return await self._t.get_bytes(f"/traces/{trace_id}/proof/pdf")
