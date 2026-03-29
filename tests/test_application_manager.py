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
        "application.auto_sort": False,
        "application.sort_by": "manual",
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


def test_launch_app_prefers_activating_existing_window_when_enabled(mock_config_manager):
    manager = ApplicationManager(mock_config_manager)
    app_info = {
        "id": "app-1",
        "path": r"C:\Program Files\Tencent\Weixin\Weixin.exe",
        "args": "",
        "prefer_activate_existing": True,
    }

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.is_dir", return_value=False), \
         patch.object(manager, "_try_activate_existing_window", return_value=True, create=True) as activate_existing, \
         patch("src.core.application_manager.os.startfile") as startfile, \
         patch("src.core.application_manager.subprocess.Popen") as popen:
        manager.launch_app(app_info)

    activate_existing.assert_called_once()
    startfile.assert_not_called()
    popen.assert_not_called()
    mock_config_manager.save_apps.assert_called_once()


def test_launch_app_falls_back_to_start_when_activation_misses(mock_config_manager):
    manager = ApplicationManager(mock_config_manager)
    app_info = {
        "id": "app-1",
        "path": r"C:\Program Files\Tencent\Weixin\Weixin.exe",
        "args": "",
        "prefer_activate_existing": True,
    }

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.is_dir", return_value=False), \
         patch.object(manager, "_try_activate_existing_window", return_value=False, create=True) as activate_existing, \
         patch("src.core.application_manager.os.startfile") as startfile, \
         patch("src.core.application_manager.subprocess.Popen") as popen:
        manager.launch_app(app_info)

    activate_existing.assert_called_once()
    assert startfile.called
    popen.assert_not_called()


def test_launch_app_keeps_existing_behavior_when_activation_disabled(mock_config_manager):
    manager = ApplicationManager(mock_config_manager)
    app_info = {
        "id": "app-1",
        "path": r"C:\Program Files\Tencent\Weixin\Weixin.exe",
        "args": "",
    }

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.is_dir", return_value=False), \
         patch.object(manager, "_try_activate_existing_window", return_value=True, create=True) as activate_existing, \
         patch("src.core.application_manager.os.startfile") as startfile, \
         patch("src.core.application_manager.subprocess.Popen") as popen:
        manager.launch_app(app_info)

    activate_existing.assert_not_called()
    assert startfile.called
    popen.assert_not_called()


def test_get_apps_does_not_sort_by_usage_even_when_enabled():
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "application.auto_sort": True,
        "application.sort_by": "usage",
    }.get(key, default)
    original_order = [
        {"id": "app-1", "name": "A", "usage_count": 1},
        {"id": "app-2", "name": "B", "usage_count": 99},
    ]
    config.get_apps.return_value = list(original_order)

    manager = ApplicationManager(config)

    apps = manager.get_apps()

    assert [a["id"] for a in apps] == [a["id"] for a in original_order]


def test_move_app_swaps_order_and_persists(mock_config_manager):
    manager = ApplicationManager(mock_config_manager)
    apps = [
        {"id": "app-1", "name": "A"},
        {"id": "app-2", "name": "B"},
    ]
    mock_config_manager.get_apps.return_value = apps

    moved = manager.move_app("app-1", 1)

    assert moved is True
    assert [a["id"] for a in apps] == ["app-2", "app-1"]
    mock_config_manager.save_apps.assert_called_once()


def test_add_folder_creates_folder_entry(mock_config_manager):
    manager = ApplicationManager(mock_config_manager)
    folder = r"C:\tmp\docs"

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.is_dir", return_value=True):
        created = manager.add_folder(folder)

    assert created["is_folder"] is True
    assert created["path"] == folder
    assert created["prefer_activate_existing"] is False
    mock_config_manager.add_app.assert_called_once()
