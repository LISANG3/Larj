#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared base helpers for Tencent plugins with credential fields.
"""

from src.core.plugin_system import PluginBase


class TencentPluginBase(PluginBase):
    def __init__(self):
        self._secret_id = ""
        self._secret_key = ""
        self._region = "ap-beijing"

    def get_secret_id(self) -> str:
        return self._secret_id

    @property
    def secret_id(self) -> str:
        return self._secret_id

    def set_secret_id(self, secret_id: str):
        self._secret_id = secret_id

    def get_secret_key(self) -> str:
        return self._secret_key

    @property
    def secret_key(self) -> str:
        return self._secret_key

    def set_secret_key(self, secret_key: str):
        self._secret_key = secret_key

    def get_region(self) -> str:
        return self._region

    @property
    def region(self) -> str:
        return self._region

    def set_region(self, region: str):
        self._region = region

    def apply_settings(self, settings: dict):
        if "secret_id" in settings:
            self.set_secret_id(settings["secret_id"])
        if "secret_key" in settings:
            self.set_secret_key(settings["secret_key"])
        if "region" in settings:
            self.set_region(settings["region"])
