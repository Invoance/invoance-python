"""Pydantic models for Invoance API request/response types.

Every model uses ``model_config = ConfigDict(extra="allow")`` so the SDK
is forward-compatible when the API adds new fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# ─── Shared ──────────────────────────────────────────────────

class PaginatedParams(BaseModel):
    """Common pagination + date-range query params."""

    model_config = ConfigDict(extra="allow")

    page: int = 1
    limit: int = 50
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class OrganizationPublic(BaseModel):
    """Issuer identity returned with GET responses."""

    model_config = ConfigDict(extra="allow")

    name: str = ""
    issuer_name: str = ""
    primary_domain: str = ""
    domain_verified: bool = False
    domain_verified_at: Optional[str] = None
    logo_url: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
#  EVENTS
# ═══════════════════════════════════════════════════════════════

class IngestEventRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_type: str
    payload: dict[str, Any]
    event_time: Optional[str] = None


class IngestEventResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    ingested_at: str


class ComplianceEvent(BaseModel):
    """Full event returned by GET /v1/events/:id."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    tenant_id: str
    event_type: str
    payload: dict[str, Any]
    event_time: Optional[str] = None
    retention_policy: str = ""
    access_tier: str = "active"
    api_key_id: Optional[str] = None
    user_id: Optional[str] = None
    ingested_at: str = ""
    payload_hash: str = ""
    request_hash: str = ""
    event_hash: str = ""
    idempotency_key: Optional[str] = None
    organization: Optional[OrganizationPublic] = None


class EventListItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    event_type: str
    payload_hash: str = ""
    event_hash: str = ""
    retention_policy: str = ""
    ingested_at: str = ""
    event_time: Optional[str] = None
    idempotency_key: Optional[str] = None


class ListEventsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    events: list[EventListItem]
    page: int
    limit: int
    total: int
    has_more: bool


class VerifyEventRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    payload_hash: Optional[str] = None
    payload: Optional[dict[str, Any]] = None


class VerifyEventResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    match_result: bool
    matched_field: Optional[str] = None
    anchored_hash: str
    submitted_hash: str
    anchored_at: str
    method: str
    organization: Optional[OrganizationPublic] = None


# ═══════════════════════════════════════════════════════════════
#  DOCUMENTS
# ═══════════════════════════════════════════════════════════════

class AnchorDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    document_hash: str
    document_ref: Optional[str] = None
    event_type: Optional[str] = None
    original_bytes_b64: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class AnchorDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    created_at: str
    document_hash: str
    status: str


class DocumentEvent(BaseModel):
    """Full document returned by GET /v1/document/:id."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    tenant_id: str
    document_ref: str = ""
    document_hash: str = ""
    signature_b64: str = ""
    signed_payload_b64: str = ""
    public_key_b64: str = ""
    has_original: bool = False
    metadata: Optional[dict[str, Any]] = None
    created_at: str = ""
    organization: Optional[OrganizationPublic] = None


class DocumentListItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    document_ref: str = ""
    document_hash: str = ""
    event_type: str = ""
    has_original: bool = False
    created_at: str = ""


class ListDocumentsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    documents: list[DocumentListItem]
    page: int
    limit: int
    total: int
    has_more: bool


class VerifyDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    document_hash: str


class VerifyDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    match_result: bool
    document_ref: str = ""
    anchored_hash: str = ""
    submitted_hash: str = ""
    anchored_at: str = ""
    organization: Optional[OrganizationPublic] = None


# ═══════════════════════════════════════════════════════════════
#  AI ATTESTATIONS
# ═══════════════════════════════════════════════════════════════

class AttestationPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    input: str
    output: str


class AttestationContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    model_provider: str
    model_name: str
    model_version: str


class AttestationSubject(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_id: Optional[str] = None
    session_id: Optional[str] = None


class IngestAttestationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    payload: AttestationPayload
    context: AttestationContext
    subject: Optional[AttestationSubject] = None


class IngestAttestationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    attestation_id: str
    created_at: str
    input_hash: str = ""
    output_hash: str = ""
    payload_hash: str = ""
    status: str = ""


class AiAttestation(BaseModel):
    """Full attestation returned by GET /v1/ai/attestations/:id."""

    model_config = ConfigDict(extra="allow")

    attestation_id: str
    tenant_id: str
    attestation_type: str = ""
    attestation_hash: str = ""
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    signed_payload: str = ""
    signature: str = ""
    public_key: str = ""
    signature_alg: str = ""
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    retention_policy: str = ""
    created_at: str = ""
    organization: Optional[OrganizationPublic] = None


class AttestationListItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    attestation_id: str
    attestation_type: str = ""
    attestation_hash: str = ""
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    retention_policy: str = ""
    created_at: str = ""


class ListAttestationsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    attestations: list[AttestationListItem]
    page: int
    limit: int
    total: int
    has_more: bool


class VerifyAttestationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    content_hash: str


class VerifyAttestationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    attestation_id: str
    match_result: bool
    matched_field: Optional[str] = None
    anchored_hash: str = ""
    submitted_hash: str = ""
    anchored_at: str = ""
    organization: Optional[OrganizationPublic] = None


# ─── Traces ──────────────────────────────────────────────────


class CreateTraceResponse(BaseModel):
    """POST /v1/traces response."""

    model_config = ConfigDict(extra="allow")

    trace_id: str
    status: str
    created_at: str
    label: str


class TraceListItem(BaseModel):
    """Single trace in a list response."""

    model_config = ConfigDict(extra="allow")

    trace_id: str
    label: str
    status: str
    event_count: Optional[int] = None
    created_at: str
    sealed_at: Optional[str] = None
    composite_hash: Optional[str] = None


class ListTracesResponse(BaseModel):
    """GET /v1/traces response."""

    model_config = ConfigDict(extra="allow")

    traces: list[TraceListItem]
    page: int
    limit: int
    total: int
    has_more: bool


class TraceEventSummary(BaseModel):
    """Event summary within a trace detail."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    event_type: str
    payload_hash: str
    ingested_at: str


class TraceDetail(BaseModel):
    """GET /v1/traces/:trace_id response with paginated events."""

    model_config = ConfigDict(extra="allow")

    trace_id: str
    label: str
    status: str
    event_count: Optional[int] = None
    created_at: str
    sealed_at: Optional[str] = None
    composite_hash: Optional[str] = None
    seal_event_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    events: list[TraceEventSummary] = []
    event_page: int = 1
    event_limit: int = 50
    event_total: int = 0
    event_has_more: bool = False


class SealTraceResponse(BaseModel):
    """POST /v1/traces/:trace_id/seal response."""

    model_config = ConfigDict(extra="allow")

    trace_id: str
    status: str
    message: str


class DeleteTraceResponse(BaseModel):
    """DELETE /v1/traces/:trace_id response."""

    model_config = ConfigDict(extra="allow")

    trace_id: str
    deleted: bool


class TraceProofEvent(BaseModel):
    """Single event in a proof bundle."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    event_type: str
    payload: dict[str, Any]
    content_hash: str
    timestamp: str
    signature: str
    public_key: str


class TraceProofSealEvent(BaseModel):
    """Seal event in a proof bundle (no payload)."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    event_type: str
    content_hash: str
    timestamp: str
    signature: str
    public_key: str


class TraceProofVerification(BaseModel):
    """Verification result in a proof bundle."""

    model_config = ConfigDict(extra="allow")

    composite_hash_valid: bool
    all_signatures_valid: bool


class TraceProofBundle(BaseModel):
    """GET /v1/traces/:trace_id/proof response."""

    model_config = ConfigDict(extra="allow")

    version: str
    trace_id: str
    label: str
    tenant_domain: Optional[str] = None
    status: str
    created_at: str
    sealed_at: str
    composite_hash: str
    event_count: int
    events: list[TraceProofEvent]
    seal_event: TraceProofSealEvent
    verification: TraceProofVerification
