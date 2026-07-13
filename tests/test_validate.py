"""Offline tests for ``client.validate()`` and ``client.me()`` — no network.

``validate()`` probes ``GET /v1/me`` (scope-free key introspection) and
classifies the outcome into a :class:`ValidationResult` without raising.
These tests patch the ``httpx.AsyncClient.request`` call the SDK makes and
assert both the wire shape (method + path) and the classification mapping.
"""

from __future__ import annotations

import httpx
import pytest

from invoance import AuthenticationError, InvoanceClient


def _client() -> InvoanceClient:
    return InvoanceClient(
        api_key="invoance_live_test_key_not_real",
        base_url="http://localhost:33100",
    )


# Full success body as documented for GET /v1/me — including a key limited
# to audit:* scopes, which the old GET /v1/events probe could 403 on.
_ME_JSON = {
    "valid": True,
    "organization": {
        "id": "org_x",
        "name": "Acme",
        "issuer_name": "Acme Corp",
        "primary_domain": "acme.example",
        "domain_verified": True,
        "plan_tier": "growth",
    },
    "tenant": {"id": "ten_x", "name": "Acme"},
    "api_key": {
        "id": "key_x",
        "name": "ci-key",
        "key_prefix": "inv_live_",
        "key_last4": "abcd",
        "scopes": ["audit:read", "audit:write"],
        "created_at": "2026-01-01T00:00:00Z",
        "last_used_at": None,
    },
    "limits": {"rate_limit_per_sec": 50},
}


def _mock_response(monkeypatch, status: int, response_json: dict) -> dict:
    """Patch httpx.AsyncClient.request to return a canned response and
    capture the outgoing method/path/params."""
    captured: dict = {}

    async def fake_request(self, method, path, *, params=None, json=None, headers=None):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        captured["params"] = params
        return httpx.Response(
            status,
            json=response_json,
            request=httpx.Request(method, f"http://localhost{path}"),
        )

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)
    return captured


async def test_validate_probes_get_me(monkeypatch) -> None:
    """validate() must hit GET /me (i.e. GET /v1/me), not the old events list."""
    captured = _mock_response(monkeypatch, 200, _ME_JSON)
    async with _client() as c:
        result = await c.validate()
    assert captured["method"] == "GET"
    assert captured["path"] == "/me"
    assert not (captured["params"] or {})  # no ?limit=1 — not the events probe
    assert result.valid is True
    assert result.reason is None
    assert result.base_url == "http://localhost:33100"


async def test_validate_succeeds_for_scope_limited_key(monkeypatch) -> None:
    """/v1/me needs no scope: a key with only audit:* scopes validates cleanly
    (the old GET /v1/events probe could 403 and misreport)."""
    captured = _mock_response(monkeypatch, 200, _ME_JSON)
    async with _client() as c:
        result = await c.validate()
    assert captured["path"] == "/me"
    assert result.valid is True
    assert result.reason is None


async def test_validate_401_means_invalid_key(monkeypatch) -> None:
    _mock_response(
        monkeypatch, 401, {"error": "invalid_api_key", "message": "Invalid API key"}
    )
    async with _client() as c:
        result = await c.validate()
    assert result.valid is False
    assert "INVOANCE_API_KEY" in (result.reason or "")


async def test_validate_403_means_authenticated_but_ip_blocked(monkeypatch) -> None:
    """403 from /v1/me is the key's IP access rules — the key itself
    authenticated, so validate() keeps reporting valid=True with a reason."""
    _mock_response(
        monkeypatch, 403, {"error": "ip_blocked", "message": "IP not allowed"}
    )
    async with _client() as c:
        result = await c.validate()
    assert result.valid is True
    assert "IP" in (result.reason or "")


async def test_validate_does_not_raise_on_network_failure(monkeypatch) -> None:
    async def fake_request(self, method, path, *, params=None, json=None, headers=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)
    async with _client() as c:
        result = await c.validate()
    assert result.valid is False
    assert "unreachable" in (result.reason or "")


# ── client.me() ──────────────────────────────────────────────


async def test_me_returns_raw_body(monkeypatch) -> None:
    captured = _mock_response(monkeypatch, 200, _ME_JSON)
    async with _client() as c:
        body = await c.me()
    assert captured["method"] == "GET"
    assert captured["path"] == "/me"
    assert body == _ME_JSON
    assert body["api_key"]["scopes"] == ["audit:read", "audit:write"]


async def test_me_raises_authentication_error_on_401(monkeypatch) -> None:
    _mock_response(
        monkeypatch, 401, {"error": "invalid_api_key", "message": "Invalid API key"}
    )
    async with _client() as c:
        with pytest.raises(AuthenticationError):
            await c.me()
