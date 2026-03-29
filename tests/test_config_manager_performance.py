#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance behavior tests for ConfigManager I/O.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

from src.core.config_manager import ConfigManager


def test_set_skips_write_when_value_unchanged():
    with tempfile.TemporaryDirectory() as td:
        old_cwd = os.getcwd()
        try:
            os.chdir(td)
            manager = ConfigManager()

            manager.set("window.width", 480)
            with patch.object(manager, "_save_settings") as mocked_save:
                manager.set("window.width", 480)
                mocked_save.assert_not_called()
        finally:
            os.chdir(old_cwd)


def test_set_many_writes_once_and_emits_once():
    with tempfile.TemporaryDirectory() as td:
        old_cwd = os.getcwd()
        try:
            os.chdir(td)
            manager = ConfigManager()
            emitted = []
            manager.config_updated.connect(lambda: emitted.append(True))

            with patch.object(manager, "_save_settings", wraps=manager._save_settings) as mocked_save:
                manager.set_many({
                    "window.width": 640,
                    "window.height": 420,
                    "search.max_results": 80,
                })

                assert mocked_save.call_count == 1
                assert len(emitted) == 1
                assert manager.get("window.width") == 640
                assert manager.get("window.height") == 420
                assert manager.get("search.max_results") == 80
        finally:
            os.chdir(old_cwd)


def test_update_config_deep_merges_nested_keys():
    with tempfile.TemporaryDirectory() as td:
        old_cwd = os.getcwd()
        try:
            os.chdir(td)
            manager = ConfigManager()
            original_height = manager.get("window.height")

            manager.update_config({"window": {"width": 700}})

            assert manager.get("window.width") == 700
            assert manager.get("window.height") == original_height
        finally:
            os.chdir(old_cwd)
