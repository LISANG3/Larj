#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtCore import QThread, pyqtSignal

from src.core.hotkey_listener import detect_hotkey


class UpdateCheckWorker(QThread):
    check_completed = pyqtSignal(object)  # UpdateInfo | None
    check_failed = pyqtSignal(str)

    def __init__(self, update_service):
        super().__init__()
        self._update_service = update_service

    def run(self):
        try:
            self.check_completed.emit(self._update_service.check_for_update())
        except Exception as e:
            self.check_failed.emit(str(e))


class UpdateDownloadWorker(QThread):
    download_completed = pyqtSignal(str)  # package path
    download_failed = pyqtSignal(str)

    def __init__(self, update_service, update_info):
        super().__init__()
        self._update_service = update_service
        self._update_info = update_info

    def run(self):
        try:
            package_path = self._update_service.download_update(self._update_info)
            self.download_completed.emit(str(package_path))
        except Exception as e:
            self.download_failed.emit(str(e))


class HotkeyDetectWorker(QThread):
    detected = pyqtSignal(str)

    def run(self):
        try:
            hotkey = detect_hotkey()
            self.detected.emit(hotkey or "")
        except Exception:
            self.detected.emit("")
