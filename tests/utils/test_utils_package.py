"""Tests for the ``sqlitch.utils`` package lazy imports."""

from __future__ import annotations

import importlib

import pytest


def test_utils_lazy_imports_cache_modules() -> None:
    """Accessing sqlitch.utils.fs should import and cache the submodule."""

    utils = importlib.import_module("sqlitch.utils")
    utils = importlib.reload(utils)
    utils.__dict__.pop("fs", None)

    assert "fs" not in utils.__dict__

    fs_module = utils.fs
    assert fs_module is importlib.import_module("sqlitch.utils.fs")

    # Attribute should now be cached in the module globals
    assert utils.__dict__["fs"] is fs_module


def test_utils_unknown_attribute_raises_attribute_error() -> None:
    """Unknown utility attributes should raise AttributeError."""

    utils = importlib.import_module("sqlitch.utils")

    with pytest.raises(AttributeError):
        _ = utils.not_a_real_helper
