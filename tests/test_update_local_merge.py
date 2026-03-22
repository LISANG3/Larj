#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for local-first config merge behavior.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config_manager import ConfigManager


def test_deep_fill_defaults_keeps_local_and_fills_missing():
    local = {
        "window": {"width": 700},
        "appearance": {"background_color": "#111111"},
    }
    defaults = {
        "window": {"width": 480, "height": 360},
        "appearance": {"background_color": "#ffffff", "accent_color": "#3b82f6"},
        "update": {"enabled": True},
    }

    with tempfile.TemporaryDirectory() as td:
        old = os.getcwd()
        try:
            os.chdir(td)
            manager = ConfigManager()
            merged = manager._deep_fill_defaults(local, defaults)
            assert merged["window"]["width"] == 700
            assert merged["window"]["height"] == 360
            assert merged["appearance"]["background_color"] == "#111111"
            assert merged["appearance"]["accent_color"] == "#3b82f6"
            assert merged["update"]["enabled"] is True
        finally:
            os.chdir(old)
