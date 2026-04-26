"""Shared client-side input validators."""

from __future__ import annotations

import re

from invoance.errors import ValidationError

_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def assert_sha256_hex(field_name: str, value: object) -> None:
    """Validate a 64-char lowercase hex SHA-256 digest.

    Raises :class:`invoance.ValidationError` with an actionable message
    when the value isn't a properly formatted hash.
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name} must be a string containing a 64-char hex "
            f"SHA-256 digest (got {type(value).__name__})"
        )
    if len(value) != 64:
        raise ValidationError(
            f"{field_name} must be 64 hex chars (got {len(value)} chars)"
        )
    if not _HEX_SHA256.match(value):
        raise ValidationError(
            f"{field_name} must be lowercase hex [0-9a-f]; "
            f"'{value[:16]}…' is not"
        )
