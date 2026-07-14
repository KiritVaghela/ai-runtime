"""Backwards-compatibility shims.

This module preserves names that were renamed or moved in previous releases
so that existing imports keep working. Deprecated aliases emit a warning and
will be removed in a future major version.

Renames:
- ``ChatSession`` -> :class:`ai_runtime.session.Session`
"""
from __future__ import annotations

import warnings

from .session import Session

_DEPRECATION_MSG = (
    "{old} is deprecated and will be removed in a future major version. "
    "Use {new} instead."
)


def __getattr__(name: str):
    """Lazy deprecation shim for renamed symbols."""
    if name == "ChatSession":
        warnings.warn(
            _DEPRECATION_MSG.format(old="ChatSession", new="Session"),
            DeprecationWarning,
            stacklevel=2,
        )
        return Session

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
