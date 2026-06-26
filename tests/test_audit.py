"""Offline tests for the audit namespace — no network, no real key.

Confirms the ``client.audit.*`` sub-resources are wired and the idempotency helper is
stable across dict ordering and distinct across content.
"""

from __future__ import annotations

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
    a = content_idempotency_key({"org": "o", "action": "x", "actor": {"id": "u1"}})
    b = content_idempotency_key({"actor": {"id": "u1"}, "action": "x", "org": "o"})  # different ordering
    c = content_idempotency_key({"org": "o", "action": "y", "actor": {"id": "u1"}})  # different content
    assert a == b
    assert a != c
    assert a.startswith("idem_")
