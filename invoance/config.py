"""SDK configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


_DEFAULT_BASE_URL = "https://api.invoance.com"
_DEFAULT_TIMEOUT = 30.0

_ENV_API_KEY = "INVOANCE_API_KEY"
_ENV_BASE_URL = "INVOANCE_BASE_URL"


@dataclass
class ClientConfig:
    """Configuration for :class:`InvoanceClient`.

    Construction is validated in :meth:`__post_init__` — the instance
    raises immediately if the API key is missing or the timeout is
    non-positive. For env-var fallback and defaulting use the
    :meth:`ClientConfig.load` factory.

    Parameters
    ----------
    api_key:
        Invoance API key (``inv_live_...`` or ``inv_test_...``).
        Required — pass explicitly, or use :meth:`load` to read
        from the ``INVOANCE_API_KEY`` environment variable.
    base_url:
        API host. Pass explicitly, or use :meth:`load` to read from
        ``INVOANCE_BASE_URL`` (defaults to ``https://api.invoance.com``).
    api_version:
        API version prefix (default ``"v1"``). Prepended to every
        request path — e.g. ``/events`` becomes ``/v1/events``.
    timeout:
        HTTP request timeout in seconds (default 30). Must be positive.
    idempotency_key:
        Optional default ``Idempotency-Key`` header for every mutating
        request. Can be overridden per-call.
    extra_headers:
        Additional headers merged into every request.
    """

    api_key: str
    base_url: str = _DEFAULT_BASE_URL
    api_version: str = "v1"
    timeout: float = _DEFAULT_TIMEOUT
    idempotency_key: str | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError(
                "api_key is required. Pass it explicitly or call "
                "ClientConfig.load() to read from the "
                f"{_ENV_API_KEY} environment variable."
            )
        if self.timeout <= 0:
            raise ValueError(
                f"timeout must be positive (got {self.timeout!r})."
            )
        # Normalize derived fields — safe because the dataclass is not frozen.
        self.base_url = self.base_url.rstrip("/")
        self.api_version = self.api_version.strip("/") or "v1"

    # ── Factory ──────────────────────────────────────────────

    @classmethod
    def load(
        cls,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        api_version: str = "v1",
        timeout: float = _DEFAULT_TIMEOUT,
        idempotency_key: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> "ClientConfig":
        """Build a ClientConfig, resolving ``api_key`` and ``base_url``
        from environment variables when not supplied explicitly.

        Precedence: explicit arg > environment variable > default.
        """
        resolved_key = api_key or os.environ.get(_ENV_API_KEY, "")
        if not resolved_key:
            raise ValueError(
                "api_key is required. Pass it explicitly or set the "
                f"{_ENV_API_KEY} environment variable."
            )
        resolved_url = (
            base_url
            or os.environ.get(_ENV_BASE_URL, "")
            or _DEFAULT_BASE_URL
        )
        return cls(
            api_key=resolved_key,
            base_url=resolved_url,
            api_version=api_version,
            timeout=timeout,
            idempotency_key=idempotency_key,
            extra_headers=extra_headers or {},
        )
