"""Offline tests for the audit namespace — no network, no real key.

Confirms the ``client.audit.*`` sub-resources are wired and the idempotency helper is
stable across dict ordering and distinct across content.
"""

from __future__ import annotations

import httpx

from invoance import InvoanceClient, content_idempotency_key


def _client() -> InvoanceClient:
    return InvoanceClient(
        api_key="invoance_live_test_key_not_real",
        base_url="http://localhost:33100",
    )


def test_audit_namespaces_present() -> None:
    c = _client()
    assert c.audit is not None
    assert c.audit.events is not None
    assert c.audit.orgs is not None
    assert c.audit.streams is not None
    assert c.audit.portal_sessions is not None
    assert c.audit.exports is not None
    # the four event verbs the README promises
    for verb in ("ingest", "list", "get", "verify"):
        assert hasattr(c.audit.events, verb)


def test_content_idempotency_key_stable_and_distinct() -> None:
    a = content_idempotency_key({"organization_id": "o", "action": "x", "actor": {"id": "u1"}})
    b = content_idempotency_key({"actor": {"id": "u1"}, "action": "x", "organization_id": "o"})  # different ordering
    c = content_idempotency_key({"organization_id": "o", "action": "y", "actor": {"id": "u1"}})  # different content
    assert a == b
    assert a != c
    assert a.startswith("idem_")


# ── request wire shape: organization_id / range_* rename (0.3.0) ──
#
# Patch the AsyncClient.request the SDK calls and capture the outgoing json/params —
# no network, and no extra test dependency (httpx is already a runtime dep).


def _capture_request(monkeypatch, response_json: dict) -> dict:
    captured: dict = {}

    async def fake_request(self, method, path, *, params=None, json=None, headers=None):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        captured["params"] = params
        return httpx.Response(
            200,
            json=response_json,
            request=httpx.Request(method, f"http://localhost{path}"),
        )

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)
    return captured


async def test_ingest_sends_organization_id_not_org(monkeypatch) -> None:
    captured = _capture_request(
        monkeypatch, {"event_id": "aevt_x", "ingested_at": "2026-01-01T00:00:00Z"}
    )
    async with _client() as c:
        await c.audit.events.ingest(
            organization_id="org_x",
            action="user.signed_in",
            actor={"type": "user", "id": "u1"},
        )
    assert captured["json"]["organization_id"] == "org_x"
    assert "org" not in captured["json"]  # the pre-0.3.0 field name must not be sent


async def test_list_sends_organization_id_and_range_params(monkeypatch) -> None:
    captured = _capture_request(monkeypatch, {"events": [], "next_cursor": None})
    async with _client() as c:
        await c.audit.events.list(
            organization_id="org_x",
            range_start="2026-01-01T00:00:00Z",
            range_end="2026-02-01T00:00:00Z",
        )
    params = captured["params"]
    assert params["organization_id"] == "org_x"
    assert params["range_start"] == "2026-01-01T00:00:00Z"
    assert params["range_end"] == "2026-02-01T00:00:00Z"
    assert "org_id" not in params
    assert "occurred_after" not in params


async def test_orgs_create_sends_organization_id_not_external_id(monkeypatch) -> None:
    captured = _capture_request(monkeypatch, {"id": "aorg_x", "organization_id": "org_x"})
    async with _client() as c:
        await c.audit.orgs.create(organization_id="org_x", name="Acme")
    assert captured["json"]["organization_id"] == "org_x"
    assert "external_id" not in captured["json"]


async def test_exports_create_sends_organization_id(monkeypatch) -> None:
    captured = _capture_request(
        monkeypatch, {"id": "aexp_x", "status": "pending", "format": "csv"}
    )
    async with _client() as c:
        await c.audit.exports.create(organization_id="org_x", format="csv")
    assert captured["json"]["organization_id"] == "org_x"
    assert "org_id" not in captured["json"]


# ── org lifecycle: update / archive / unarchive / delete / include_archived ──


_ORG_JSON = {
    "id": "aorg_x",
    "organization_id": "org_x",
    "external_id": "org_x",
    "name": "Acme",
    "retention_days": 90,
    "created_at": "2026-01-01T00:00:00Z",
    "archived_at": None,
}


async def test_orgs_update_sends_patch_with_name(monkeypatch) -> None:
    captured = _capture_request(monkeypatch, {**_ORG_JSON, "name": "Acme Renamed"})
    async with _client() as c:
        await c.audit.orgs.update("org_x", name="Acme Renamed")
    assert captured["method"] == "PATCH"
    assert captured["path"] == "/audit/orgs/org_x"
    assert captured["json"] == {"name": "Acme Renamed"}


async def test_orgs_update_none_sends_json_null_to_clear(monkeypatch) -> None:
    captured = _capture_request(monkeypatch, {**_ORG_JSON, "name": None})
    async with _client() as c:
        await c.audit.orgs.update("org_x", name=None)
    assert captured["method"] == "PATCH"
    assert captured["json"] == {"name": None}  # serialized as JSON null on the wire


async def test_orgs_archive_posts_to_archive_path(monkeypatch) -> None:
    captured = _capture_request(
        monkeypatch, {**_ORG_JSON, "archived_at": "2026-07-13T00:00:00Z"}
    )
    async with _client() as c:
        await c.audit.orgs.archive("aorg_x")
    assert captured["method"] == "POST"
    assert captured["path"] == "/audit/orgs/aorg_x/archive"
    assert captured["json"] is None


async def test_orgs_unarchive_posts_to_unarchive_path(monkeypatch) -> None:
    captured = _capture_request(monkeypatch, _ORG_JSON)
    async with _client() as c:
        await c.audit.orgs.unarchive("aorg_x")
    assert captured["method"] == "POST"
    assert captured["path"] == "/audit/orgs/aorg_x/unarchive"


async def test_orgs_delete_uses_delete_method(monkeypatch) -> None:
    captured = _capture_request(monkeypatch, {"deleted": True, "id": "aorg_x"})
    async with _client() as c:
        await c.audit.orgs.delete("aorg_x")
    assert captured["method"] == "DELETE"
    assert captured["path"] == "/audit/orgs/aorg_x"


async def test_orgs_list_excludes_archived_by_default(monkeypatch) -> None:
    captured = _capture_request(monkeypatch, {"orgs": []})
    async with _client() as c:
        await c.audit.orgs.list()
    assert captured["method"] == "GET"
    assert captured["path"] == "/audit/orgs"
    assert not (captured["params"] or {})  # no include_archived param sent


async def test_orgs_list_include_archived_sends_query_param(monkeypatch) -> None:
    captured = _capture_request(monkeypatch, {"orgs": []})
    async with _client() as c:
        await c.audit.orgs.list(include_archived=True)
    assert captured["params"]["include_archived"] == "true"
