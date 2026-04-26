"""Documents resource – ``client.documents.*``"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Any, Union

from invoance._internal.http import HttpTransport
from invoance._internal.validate import assert_sha256_hex
from invoance.models import (
    AnchorDocumentResponse,
    DocumentEvent,
    ListDocumentsResponse,
    VerifyDocumentResponse,
)


class DocumentsResource:
    """Namespace for ``/document`` endpoints."""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    # ── POST /document/anchor ─────────────────────────────

    async def anchor(
        self,
        *,
        document_hash: str,
        document_ref: str | None = None,
        event_type: str | None = None,
        original_bytes_b64: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        trace_id: str | None = None,
    ) -> AnchorDocumentResponse:
        """Anchor a document hash.

        Parameters
        ----------
        document_hash:
            Hex-encoded SHA-256 of the document (64 chars).
        document_ref:
            Human-readable reference (e.g. filename).
        event_type:
            Classification string.
        original_bytes_b64:
            Base64-encoded original file (stored encrypted, optional).
        metadata:
            Arbitrary JSON metadata.
        idempotency_key:
            Optional idempotency header for safe retries.
        """
        assert_sha256_hex("document_hash", document_hash)

        body: dict[str, Any] = {"document_hash": document_hash}
        if document_ref is not None:
            body["document_ref"] = document_ref
        if event_type is not None:
            body["event_type"] = event_type
        if original_bytes_b64 is not None:
            body["original_bytes_b64"] = original_bytes_b64
        if metadata is not None:
            body["metadata"] = metadata
        if trace_id is not None:
            body["trace_id"] = trace_id

        raw = await self._t.post(
            "/document/anchor",
            json=body,
            idempotency_key=idempotency_key,
        )
        return AnchorDocumentResponse.model_validate(raw)

    # ── POST /document/anchor (file helper) ────────────────

    async def anchor_file(
        self,
        *,
        file: Union[str, Path, bytes],
        document_ref: str | None = None,
        event_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        skip_original: bool = False,
        trace_id: str | None = None,
    ) -> AnchorDocumentResponse:
        """Convenience helper — reads a file, computes its SHA-256 hash,
        base64-encodes the bytes, and calls :meth:`anchor`.

        Parameters
        ----------
        file:
            A file path (``str`` or ``Path``), or raw ``bytes``.
        document_ref:
            Human-readable reference. Defaults to the filename when a
            path is provided.
        event_type:
            Classification string (e.g. ``"invoice"``, ``"contract"``).
        metadata:
            Arbitrary JSON metadata attached to the anchor.
        idempotency_key:
            Optional idempotency header for safe retries.
        skip_original:
            If ``True``, do not upload the original file bytes.

        Example
        -------
        ::

            result = await client.documents.anchor_file(
                file="./invoice.pdf",
                document_ref="Invoice #1042",
            )
            print(result.event_id)
        """
        if isinstance(file, (str, Path)):
            path = Path(file)
            content = path.read_bytes()
            if document_ref is None:
                document_ref = path.name
        else:
            content = file

        document_hash = hashlib.sha256(content).hexdigest()

        return await self.anchor(
            document_hash=document_hash,
            document_ref=document_ref,
            event_type=event_type,
            metadata=metadata,
            idempotency_key=idempotency_key,
            original_bytes_b64=None if skip_original else base64.b64encode(content).decode(),
            trace_id=trace_id,
        )

    # ── GET /document ─────────────────────────────────────

    async def list(
        self,
        *,
        page: int = 1,
        limit: int = 50,
        date_from: str | None = None,
        date_to: str | None = None,
        document_ref: str | None = None,
    ) -> ListDocumentsResponse:
        """Paginated document listing (max 500 per page, cached 30 s)."""
        raw = await self._t.get(
            "/document",
            params={
                "page": page,
                "limit": limit,
                "date_from": date_from,
                "date_to": date_to,
                "document_ref": document_ref,
            },
        )
        return ListDocumentsResponse.model_validate(raw)

    # ── GET /document/:event_id ───────────────────────────

    async def get(self, event_id: str) -> DocumentEvent:
        """Retrieve a single document by event ID."""
        raw = await self._t.get(f"/document/{event_id}")
        return DocumentEvent.model_validate(raw)

    # ── GET /document/:event_id/original ──────────────────

    async def get_original(self, event_id: str) -> bytes:
        """Download the original document file as raw bytes.

        Returns the original file that was uploaded with the anchor
        request. Cached server-side for 5 minutes.
        """
        return await self._t.get_bytes(f"/document/{event_id}/original")

    # ── POST /document/:event_id/verify ───────────────────

    async def verify(
        self,
        event_id: str,
        *,
        document_hash: str,
    ) -> VerifyDocumentResponse:
        """Compare a hash against the anchored document hash.

        Parameters
        ----------
        event_id:
            The document's event ID.
        document_hash:
            Hex-encoded SHA-256 to verify (64 chars).
        """
        assert_sha256_hex("document_hash", document_hash)
        raw = await self._t.post(
            f"/document/{event_id}/verify",
            json={"document_hash": document_hash},
        )
        return VerifyDocumentResponse.model_validate(raw)
