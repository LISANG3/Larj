#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance behavior tests for MainPanel app grid rendering.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QApplication, QToolButton

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

from src.ui.main_panel import MainPanel


class _DummySignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, _fn):
        self._callbacks.append(_fn)
        return None


class _DummySearchEngine:
    def __init__(self):
        self.search_completed = _DummySignal()
        self.search_failed = _DummySignal()

    def search(self, _text):
        return None

    def cancel_search(self):
        return None


def _build_panel(apps):
    config_manager = MagicMock()
    config_manager.get.side_effect = lambda key, default=None: default
    config_manager.get_apps.return_value = apps

    application_manager = MagicMock()
    application_manager.get_apps.return_value = apps
    application_manager.launch_app.return_value = None
    application_manager.update_app.return_value = None
    application_manager.remove_app.return_value = None
    application_manager.add_app.return_value = None

    plugin_system = SimpleNamespace(plugins={})
    search_engine = _DummySearchEngine()

    with patch.object(MainPanel, "_start_mouse_listener", lambda self: None), \
            patch("src.ui.main_panel.extract_icon_from_file", return_value=QToolButton().icon()):
        panel = MainPanel(config_manager, search_engine, application_manager, plugin_system)
    return panel


def test_load_apps_skips_rebuild_when_state_unchanged():
    panel = _build_panel([{"id": "app-1", "name": "A", "path": "a.exe"}])
    panel._create_app_button = MagicMock(return_value=QToolButton())

    panel._load_apps(force=True)
    panel._create_app_button.reset_mock()

    panel._load_apps()
    panel._create_app_button.assert_not_called()


def test_load_apps_force_rebuild_even_when_state_unchanged():
    panel = _build_panel([{"id": "app-1", "name": "A", "path": "a.exe"}])
    panel._create_app_button = MagicMock(return_value=QToolButton())

    panel._load_apps(force=True)
    panel._create_app_button.reset_mock()

    panel._load_apps(force=True)
    assert panel._create_app_button.call_count == 1


def test_global_mouse_click_hides_panel_without_cross_thread_qwidget_access():
    panel = _build_panel([{"id": "app-1", "name": "A", "path": "a.exe"}])
    panel.show = MagicMock()
    panel.hide = MagicMock()
    panel.reset_panel_state = MagicMock()
    panel._settings_dialog = None
    panel.config_manager.get.side_effect = lambda key, default=None: True if key == "window.hide_on_focus_loss" else default

    with patch.object(panel, "isVisible", return_value=True), \
            patch.object(panel, "mapFromGlobal", return_value=panel.rect().bottomRight() + panel.rect().center()):
        panel._on_global_mouse_click(9999, 9999)

    panel.hide.assert_called_once()
    panel.reset_panel_state.assert_called_once()
