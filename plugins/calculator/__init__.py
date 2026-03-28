#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calculator Plugin - Quick system calculator launcher.
"""

import logging
import subprocess

from src.core.plugin_system import PluginBase


class CalculatorPlugin(PluginBase):
    """Simple calculator launcher plugin."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_metadata(self) -> dict:
        return {
            "plugin_id": "calculator",
            "name": "Calculator",
            "icon": "calculator",
            "version": "1.0.0",
            "author": "Larj Team",
            "description": "快速启动系统计算器",
            "config_schema": {},
        }

    def handle_click(self):
        try:
            subprocess.Popen(["calc.exe"])
        except Exception as e:
            self.logger.error(f"Failed to launch calculator: {e}", exc_info=True)


plugin_class = CalculatorPlugin
