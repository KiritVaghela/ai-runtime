import warnings

import pytest

import ai_runtime.compat as compat
from ai_runtime.session import Session


def test_chatsession_shim_resolves_to_session():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolved = compat.ChatSession

    assert resolved is Session
    assert any(
        issubclass(w.category, DeprecationWarning) for w in caught
    )


def test_unknown_attribute_raises():
    with pytest.raises(AttributeError):
        _ = compat.DoesNotExist
