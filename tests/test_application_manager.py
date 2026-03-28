#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance-oriented tests for ApplicationManager.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

from src.core.application_manager import ApplicationManager


@pytest.fixture
def mock_config_manager():
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "application.auto_sort": True,
        "application.sort_by": "usage",
    }.get(key, default)
    config.get_apps.return_value = [{"id": "app-1", "name": "A", "usage_count": 0}]
    return config


def test_update_usage_stats_reuses_loaded_apps_cache(mock_config_manager):
    manager = ApplicationManager(mock_config_manager)

    manager._update_usage_stats("app-1")
    manager._update_usage_stats("app-1")

    assert mock_config_manager.get_apps.call_count == 1
    assert mock_config_manager.save_apps.call_count == 2


def test_update_usage_stats_missing_app_avoids_disk_write(mock_config_manager):
    manager = ApplicationManager(mock_config_manager)

    manager._update_usage_stats("missing-id")

    mock_config_manager.save_apps.assert_not_called()


def test_split_launch_args_handles_empty_and_quoted():
    assert ApplicationManager._split_launch_args("") == []
    assert ApplicationManager._split_launch_args(' --mode "safe run" ') == ["--mode", "safe run"]


def test_launch_app_uses_startfile_without_shell(mock_config_manager):
    manager = ApplicationManager(mock_config_manager)
    app_info = {"id": "app-1", "path": r"C:\Windows\notepad.exe", "args": "--help"}

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.is_dir", return_value=False), \
         patch("src.core.application_manager.os.startfile") as startfile, \
         patch("src.core.application_manager.subprocess.Popen") as popen:
        manager.launch_app(app_info)

    assert startfile.called
    popen.assert_not_called()
