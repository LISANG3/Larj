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
