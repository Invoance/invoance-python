"""Low-level HTTP transport shared by all resource classes."""

from __future__ import annotations

from typing import Any

import httpx

from invoance.config import ClientConfig
from invoance.errors import (
    NetworkError,
    RequestContext,
    TimeoutError as InvoanceTimeoutError,
    raise_for_status,
)
from invoance._version import SDK_VERSION


class HttpTransport:
    """Thin wrapper around ``httpx.AsyncClient`` that handles auth,
    base URL joining, and automatic error raising.

    Network-level failures (DNS, connection refused, timeouts) are
    translated into :class:`invoance.NetworkError` /
    :class:`invoance.TimeoutError` so a single ``except InvoanceError``
    covers everything the SDK can throw.
    """

    def __init__(self, config: ClientConfig) -> None:
        self._config = config
        version = config.api_version.strip("/")
        self._client = httpx.AsyncClient(
            base_url=f"{config.base_url}/{version}",
            timeout=config.timeout,
            headers=self._build_headers(),
        )

    # ── Public interface ─────────────────────────────────────

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ctx = RequestContext(method="GET", path=path)
        resp = await self._request("GET", path, params=_strip_none(params), ctx=ctx)
        return self._handle(resp, ctx)

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        idem = idempotency_key or self._config.idempotency_key
        if idem:
            headers["Idempotency-Key"] = idem

        ctx = RequestContext(method="POST", path=path)
        resp = await self._request(
            "POST", path, json=json, headers=headers, ctx=ctx,
        )
        return self._handle(resp, ctx)

    async def delete(
        self,
        path: str,
    ) -> dict[str, Any]:
        ctx = RequestContext(method="DELETE", path=path)
        resp = await self._request("DELETE", path, ctx=ctx)
        return self._handle(resp, ctx)

    async def get_bytes(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> bytes:
        """GET that returns raw bytes instead of parsed JSON."""
        ctx = RequestContext(method="GET", path=path)
        resp = await self._request("GET", path, params=_strip_none(params), ctx=ctx)
        if resp.status_code < 200 or resp.status_code >= 300:
            try:
                body = resp.json()
            except Exception:
                body = None
            raise_for_status(
                resp.status_code,
                body,
                request=ctx,
                retry_after_seconds=_parse_retry_after(resp.headers.get("retry-after")),
            )
        return resp.content

    async def close(self) -> None:
        await self._client.aclose()

    # ── Internals ────────────────────────────────────────────

    def _build_headers(self) -> dict[str, str]:
        h: dict[str, str] = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Accept": "application/json",
            "User-Agent": f"invoance-python/{SDK_VERSION}",
        }
        h.update(self._config.extra_headers)
        return h

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        ctx: RequestContext,
    ) -> httpx.Response:
        """Perform a request, translating transport errors into SDK errors."""
        try:
            return await self._client.request(
                method, path, params=params, json=json, headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise InvoanceTimeoutError(
                f"Request timed out after {self._config.timeout}s on {method} {path}",
                request=ctx,
            ) from exc
        except httpx.HTTPError as exc:
            raise NetworkError(
                f"Network failure on {method} {path}: {exc}",
                request=ctx,
            ) from exc

    @staticmethod
    def _handle(resp: httpx.Response, ctx: RequestContext) -> dict[str, Any]:
        try:
            body = resp.json()
        except Exception:
            body = None

        raise_for_status(
            resp.status_code,
            body,
            request=ctx,
            retry_after_seconds=_parse_retry_after(resp.headers.get("retry-after")),
        )
        return body


def _strip_none(d: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove keys whose value is None so they don't pollute query strings."""
    if d is None:
        return None
    return {k: v for k, v in d.items() if v is not None}


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header — seconds or HTTP-date form."""
    if not value:
        return None
    try:
        seconds = float(value)
        if seconds >= 0:
            return seconds
    except ValueError:
        pass
    # HTTP-date form
    try:
        from email.utils import parsedate_to_datetime
        from datetime import datetime, timezone

        dt = parsedate_to_datetime(value)
        if dt is not None:
            delta = (dt - datetime.now(tz=timezone.utc)).total_seconds()
            return max(0.0, delta)
    except Exception:
        return None
    return None
