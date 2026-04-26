"""Single source of truth for the SDK version.

Read from the installed package metadata so the User-Agent header never
drifts from the published version. Falls back to the in-source constant
when the package isn't installed (e.g. running tests against source).
"""

from __future__ import annotations

try:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError

    try:
        SDK_VERSION: str = _pkg_version("invoance")
    except PackageNotFoundError:  # pragma: no cover – source checkout
        SDK_VERSION = "0.1.0"
except ImportError:  # pragma: no cover – py<3.8, not supported but harmless
    SDK_VERSION = "0.1.0"
