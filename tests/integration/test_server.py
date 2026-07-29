# -*- coding: utf-8 -*-
"""Integration tests for the FastAPI application bootstrap."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def test_server_module_can_be_parsed():
    """The server module must be syntactically valid and compile."""
    server_path = ROOT / "server.py"
    assert server_path.exists()
    spec = importlib.util.spec_from_file_location("server", str(server_path))
    assert spec is not None and spec.loader is not None
    source = server_path.read_text(encoding="utf-8")
    compiled = compile(source, str(server_path), "exec")
    assert compiled is not None


def test_app_config_has_expected_values():
    """Sanity check for critical configuration defaults."""
    sys.path.insert(0, str(ROOT))
    try:
        from app_config import APP_TITLE, APP_VERSION, DEFAULT_PORT

        assert APP_TITLE == "MPFM Manager"
        assert APP_VERSION == "4.1"
        assert isinstance(DEFAULT_PORT, int)
        assert DEFAULT_PORT > 0
    finally:
        if str(ROOT) in sys.path:
            sys.path.remove(str(ROOT))
