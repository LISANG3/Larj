#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compatibility proxy module.

Keep `plugins.mtran_server` as the canonical translation plugin implementation.
This package-level module now re-exports that implementation for backward compatibility.
"""

from plugins.mtran_server import TencentTranslationPlugin, plugin_class

__all__ = ["TencentTranslationPlugin", "plugin_class"]
