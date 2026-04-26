"""Smoke tests — verifies the package imports and basic instantiation works.

These tests run without network access and without requiring a real
INVOANCE_API_KEY. Their job is to catch import-level breakage (broken
__init__.py, missing dependencies, syntax errors) before publish, not
to verify API behavior. Functional tests against a real backend live
in `examples/` and are run by hand.
"""

from __future__ import annotations

import pytest


def test_top_level_imports() -> None:
    """Every name promised by the README must import from the top-level package."""
    from invoance import (
        InvoanceClient,
        ClientConfig,
        InvoanceError,
        AuthenticationError,
        QuotaExceededError,
        ValidationError,
        TimeoutError,
        NetworkError,
    )

    # Just touch each so static analyzers don't drop the imports.
    assert InvoanceClient is not None
    assert ClientConfig is not None
    assert InvoanceError is not None
    assert AuthenticationError is not None
    assert QuotaExceededError is not None
    assert ValidationError is not None
    assert TimeoutError is not None
    assert NetworkError is not None


def test_client_constructs_with_explicit_args() -> None:
    """InvoanceClient(api_key=..., base_url=...) must succeed without env vars."""
    from invoance import InvoanceClient

    client = InvoanceClient(
        api_key="invoance_live_test_key_not_real",
        base_url="https://api.invoance.com",
        timeout=10.0,
    )
    assert client is not None


def test_client_raises_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """No api_key (explicit or env) should fail loudly, not silently."""
    monkeypatch.delenv("INVOANCE_API_KEY", raising=False)

    from invoance import InvoanceClient
    from invoance.errors import InvoanceError

    with pytest.raises((InvoanceError, ValueError, TypeError)):
        InvoanceClient()


def test_error_hierarchy() -> None:
    """All concrete error classes must inherit from InvoanceError so
    consumers can catch the base type and handle anything."""
    from invoance import (
        InvoanceError,
        AuthenticationError,
        QuotaExceededError,
        ValidationError,
        TimeoutError,
        NetworkError,
    )

    for cls in (
        AuthenticationError,
        QuotaExceededError,
        ValidationError,
        TimeoutError,
        NetworkError,
    ):
        assert issubclass(cls, InvoanceError), f"{cls.__name__} must extend InvoanceError"
