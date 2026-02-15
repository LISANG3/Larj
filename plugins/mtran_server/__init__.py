#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTranServer Plugin
Quick access entry for local MTranServer translation service.
"""

import logging
import urllib.error
import urllib.request
import webbrowser

from src.core.plugin_system import PluginBase


class MTranServerPlugin(PluginBase):
    """Open local MTranServer UI or project homepage."""

    UI_URL = "http://127.0.0.1:8989/ui/"
    HOME_URL = "https://github.com/xxnuo/MTranServer"
    CONNECTION_TIMEOUT = 1

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_name(self) -> str:
        return "MTranServer"

    def get_icon(self) -> str:
        return "translate"

    def get_info(self) -> dict:
        return {
            "name": "MTranServer",
            "version": "1.0.0",
            "author": "Larj Team",
            "description": "Offline translation quick entry (优先打开本地 MTranServer)"
        }

    def handle_click(self):
        """Open local MTranServer UI when available."""
        webbrowser.open(self.UI_URL if self._is_local_server_online() else self.HOME_URL)

    def _is_local_server_online(self) -> bool:
        try:
            with urllib.request.urlopen(self.UI_URL, timeout=self.CONNECTION_TIMEOUT):
                return True
        except (urllib.error.URLError, ValueError, TimeoutError):
            return False

    def on_load(self):
        self.logger.info("MTranServer plugin loaded")

    def on_unload(self):
        self.logger.info("MTranServer plugin unloaded")
