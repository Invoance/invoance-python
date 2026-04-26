"""SDK error hierarchy.

Every error raised by the SDK — API responses, network failures, and
client-side validation — inherits from :class:`InvoanceError`, so a
single ``except InvoanceError`` is enough to catch anything the SDK
throws.

    try:
        event = await client.events.ingest(...)
    except invoance.QuotaExceededError:
        print("Upgrade your plan")
    except invoance.TimeoutError:
        print("Request timed out — retrying")
    except invoance.InvoanceError as exc:
        print(f"Invoance error: {exc}")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RequestContext:
    """HTTP method + path that produced the error (for message context)."""

    method: str
    path: str


class InvoanceError(Exception):
    """Base class for all SDK errors.

    Attributes
    ----------
    status_code:
        HTTP status code, or ``None`` for client-side / transport errors.
    error_code:
        Machine-readable error code from the server ``error`` field.
    body:
        Parsed JSON response body, when available.
    request:
        Request context (method + path) for error message construction.
    retry_after_seconds:
        Value of the server's ``Retry-After`` header, when present.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        body: dict[str, Any] | None = None,
        request: RequestContext | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.body = body
        self.request = request
        self.retry_after_seconds = retry_after_seconds

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"status={self.status_code}, "
            f"code={self.error_code!r}, "
            f"message={str(self)!r})"
        )


class AuthenticationError(InvoanceError):
    """401 – invalid or missing API key."""


class ForbiddenError(InvoanceError):
    """403 – API key lacks required permission scope."""


class NotFoundError(InvoanceError):
    """404 – resource does not exist or has expired."""


class ValidationError(InvoanceError):
    """400 – bad request / validation failure (server-side **or** client-side)."""


class ConflictError(InvoanceError):
    """409 – idempotency conflict."""


class QuotaExceededError(InvoanceError):
    """429 – plan quota exceeded."""


class ServerError(InvoanceError):
    """5xx – something went wrong on the server."""


class NetworkError(InvoanceError):
    """Raised when the request fails before a response is received.

    DNS failure, connection refused, TLS handshake error, reset, etc.
    """


class TimeoutError(InvoanceError):  # noqa: A001 – intentional shadow of builtin, callers import `invoance.TimeoutError`
    """Raised when the request exceeds the configured ``timeout``."""


# Status code → exception class mapping
_STATUS_MAP: dict[int, type[InvoanceError]] = {
    400: ValidationError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    429: QuotaExceededError,
}


def _describe_request(ctx: RequestContext | None) -> str:
    return f" on {ctx.method} {ctx.path}" if ctx is not None else ""


def raise_for_status(
    status_code: int,
    body: dict[str, Any] | None,
    *,
    request: RequestContext | None = None,
    retry_after_seconds: float | None = None,
) -> None:
    """Raise the appropriate :class:`InvoanceError` subclass for a failed response."""
    if 200 <= status_code < 300:
        return

    body = body or {}
    error_code = body.get("error", "unknown")
    server_message = body.get("message")

    if server_message:
        message = server_message
    elif status_code == 429 and retry_after_seconds is not None:
        message = (
            f"HTTP 429{_describe_request(request)} — rate limited, "
            f"retry after {retry_after_seconds}s"
        )
    else:
        message = (
            f"HTTP {status_code}{_describe_request(request)} (no response body)"
        )

    exc_cls = _STATUS_MAP.get(status_code)
    if exc_cls is None:
        exc_cls = ServerError if status_code >= 500 else InvoanceError

    raise exc_cls(
        message,
        status_code=status_code,
        error_code=error_code,
        body=body,
        request=request,
        retry_after_seconds=retry_after_seconds,
    )
