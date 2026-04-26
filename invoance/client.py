"""Top-level SDK client.

Usage
-----
::

    from invoance import InvoanceClient

    # Reads INVOANCE_API_KEY and INVOANCE_BASE_URL from env automatically
    async with InvoanceClient() as client:
        event = await client.events.ingest(event_type="user.login", payload={...})
        doc   = await client.documents.anchor(document_hash="abcd...")
        att   = await client.attestations.ingest(
            attestation_type="output", input="...", output="...", ...
        )

    # Or pass explicitly to override env
    async with InvoanceClient(api_key="inv_live_abc123", base_url="http://localhost:33100") as client:
        ...

    # Or use a full config object
    from invoance import ClientConfig
    client = InvoanceClient(config=ClientConfig(api_key="inv_test_xyz"))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from invoance._internal.http import HttpTransport
from invoance.config import ClientConfig
from invoance.errors import (
    AuthenticationError,
    ForbiddenError,
    InvoanceError,
    NetworkError,
    QuotaExceededError,
)
from invoance.errors import TimeoutError as InvoanceTimeoutError
from invoance.resources.events import EventsResource
from invoance.resources.documents import DocumentsResource
from invoance.resources.attestations import AttestationsResource
from invoance.resources.traces import TracesResource


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of :meth:`InvoanceClient.validate`.

    ``valid=True`` means the API key was accepted by the server (2xx,
    403, or 429 — 403 and 429 still prove the key authenticated).
    ``valid=False`` means the key was rejected, or the request never
    reached the server. ``reason`` is populated whenever it carries
    useful information.
    """

    valid: bool
    reason: Optional[str]
    base_url: str


class InvoanceClient:
    """Async client for the Invoance compliance API.

    All parameters are optional. When omitted the client reads from
    environment variables:

    - ``INVOANCE_API_KEY``  — API key (required)
    - ``INVOANCE_BASE_URL`` — API host (defaults to ``https://api.invoance.com``)

    Parameters
    ----------
    api_key:
        Override the API key (instead of reading from env).
    base_url:
        Override the API host (instead of reading from env).
    timeout:
        HTTP request timeout in seconds (default 30). Must be positive.
    config:
        Pre-built :class:`ClientConfig`. Mutually exclusive with
        ``api_key``, ``base_url``, and ``timeout`` — pass a config OR
        the individual overrides, never both.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        config: ClientConfig | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        if config is not None and (
            api_key is not None
            or base_url is not None
            or timeout is not None
        ):
            raise ValueError(
                "Pass `config` OR individual overrides "
                "(`api_key`, `base_url`, `timeout`), not both."
            )

        if config is None:
            load_kwargs: dict = {}
            if api_key is not None:
                load_kwargs["api_key"] = api_key
            if base_url is not None:
                load_kwargs["base_url"] = base_url
            if timeout is not None:
                load_kwargs["timeout"] = timeout
            config = ClientConfig.load(**load_kwargs)

        self._transport = HttpTransport(config)
        self._config = config

        # Resource namespaces
        self.events = EventsResource(self._transport)
        self.documents = DocumentsResource(self._transport)
        self.attestations = AttestationsResource(self._transport)
        self.traces = TracesResource(self._transport)

    @property
    def config(self) -> ClientConfig:
        return self._config

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._transport.close()

    # ── Quick validation ─────────────────────────────────────

    async def validate(self) -> ValidationResult:
        """Probe a cheap authenticated endpoint to confirm the API key works.

        Issues ``GET /v1/events?limit=1`` and classifies the outcome.
        Does not raise — every failure mode (bad key, network down,
        timeout, 5xx) is converted into a :class:`ValidationResult`
        the caller can inspect.

        ::

            result = await client.validate()
            if not result.valid:
                raise RuntimeError(f"bad Invoance config: {result.reason}")
        """
        base_url = self._config.base_url
        try:
            await self.events.list(limit=1)
            return ValidationResult(valid=True, reason=None, base_url=base_url)
        except AuthenticationError:
            return ValidationResult(
                valid=False,
                reason="Authentication failed — check INVOANCE_API_KEY",
                base_url=base_url,
            )
        except ForbiddenError:
            return ValidationResult(
                valid=True,
                reason="API key authenticated but lacks permission to list events",
                base_url=base_url,
            )
        except QuotaExceededError:
            return ValidationResult(
                valid=True,
                reason="API key authenticated but currently rate limited",
                base_url=base_url,
            )
        except (NetworkError, InvoanceTimeoutError) as exc:
            return ValidationResult(
                valid=False,
                reason=f"Server unreachable: {exc}",
                base_url=base_url,
            )
        except InvoanceError as exc:
            return ValidationResult(
                valid=False,
                reason=str(exc),
                base_url=base_url,
            )

    # ── Context manager ──────────────────────────────────────

    async def __aenter__(self) -> "InvoanceClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
