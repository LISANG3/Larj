#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tencent OCR Plugin - Screen text recognition using Tencent Cloud OCR API
Click plugin to start area screenshot, then recognize text and display result
"""

import base64
import json
import logging
import os
import tempfile
from typing import Dict, List

import requests
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QWidget, QApplication
)
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QThread
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QGuiApplication

from src.plugins.tencent_signer import TencentSigner
from src.plugins.tencent_plugin_base import TencentPluginBase


class OcrWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, secret_id: str, secret_key: str, region: str, image_path: str):
        super().__init__()
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.image_path = image_path

    def run(self):
        try:
            if not self.secret_id or not self.secret_key:
                self.error.emit("请先在设置中配置 SecretId 和 SecretKey")
                return

            with open(self.image_path, "rb") as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            service = "ocr"
            host = "ocr.tencentcloudapi.com"
            action = "GeneralAccurateOCR"
            version = "2018-11-19"
            payload = json.dumps({"ImageBase64": image_base64})

            headers = TencentSigner.sign(
                self.secret_id,
                self.secret_key,
                service,
                host,
                action,
                version,
                self.region,
                payload,
            )
            response = requests.post(f"https://{host}/", headers=headers, data=payload, timeout=30)
            if response.status_code != 200:
                self.error.emit(f"HTTP错误: {response.status_code}")
                return

            result = response.json()
            response_obj = result.get("Response")
            if not isinstance(response_obj, dict):
                self.error.emit("响应格式错误")
                return
            if "Error" in response_obj:
                error_msg = response_obj["Error"].get("Message", "Unknown error")
                self.error.emit(f"API错误: {error_msg}")
                return
            self.finished.emit(response_obj.get("TextDetections", []))
        except requests.exceptions.Timeout:
            self.error.emit("请求超时")
        except requests.exceptions.ConnectionError:
            self.error.emit("网络连接失败")
        except Exception as e:
            self.error.emit(f"识别失败: {e}")


class ScreenCaptureWidget(QWidget):
    """Full screen widget for selecting capture area"""
    
    capture_finished = pyqtSignal(QRect)
    
    def __init__(self):
        super().__init__()
        self.start_pos = None
        self.end_pos = None
        self.is_selecting = False
        
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowFullScreen)
        self.setCursor(Qt.CrossCursor)
        
        screen = QGuiApplication.primaryScreen()
        self.screen_geometry = screen.geometry()
        self.setGeometry(self.screen_geometry)
        
        self.screenshot = screen.grabWindow(0)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.screenshot)
        
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        if self.start_pos and self.end_pos:
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()
            
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(selection_rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            
            painter.drawPixmap(selection_rect, self.screenshot, selection_rect)
            
            painter.setPen(QPen(QColor("#3b82f6"), 2, Qt.DashLine))
            painter.drawRect(selection_rect)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.is_selecting = True
            self.update()
    
    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            if self.start_pos and self.end_pos:
                rect = QRect(self.start_pos, self.end_pos).normalized()
                if rect.width() > 10 and rect.height() > 10:
                    self.capture_finished.emit(rect)
            self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class OcrResultDialog(QDialog):
    """Dialog to display OCR result"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OCR 识别结果")
        self.setMinimumSize(500, 400)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("识别结果")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
        """)
        layout.addWidget(title_label)
        
        self.result_text = QTextEdit()
        self.result_text.setPlaceholderText("识别中...")
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                background: #f8fafc;
                color: #1e293b;
            }
        """)
        layout.addWidget(self.result_text)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        copy_btn = QPushButton("复制")
        copy_btn.setFixedHeight(36)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: 500;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #2563eb;
            }
        """)
        copy_btn.clicked.connect(self.copy_result)
        btn_layout.addWidget(copy_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.setFixedHeight(36)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #475569;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: 500;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #e2e8f0;
            }
        """)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def set_result(self, text_detections: List[Dict]):
        if not text_detections:
            self.result_text.setPlainText("未识别到文字")
            return
        
        lines = []
        for item in text_detections:
            text = item.get("DetectedText", "")
            if text:
                lines.append(text)
        
        self.result_text.setPlainText("\n".join(lines))
    
    def set_error(self, error_msg: str):
        self.result_text.setPlainText(f"错误: {error_msg}")
    
    def copy_result(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.result_text.toPlainText())


class TencentOcrPlugin(TencentPluginBase):
    """Tencent Cloud OCR Plugin for screen text recognition"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._capture_widget = None
        self._result_dialog = None
        self._temp_image_path = None
        self._ocr_worker = None
    
    def get_metadata(self) -> dict:
        return {
            "plugin_id": "ocr",
            "name": "OCR 识别",
            "icon": "scan",
            "version": "1.0.0",
            "author": "Larj Team",
            "description": "屏幕文字识别 - 腾讯云 OCR",
            "config_schema": {
                "secret_id": {"type": "str", "required": True, "desc": "腾讯云 API 密钥 ID"},
                "secret_key": {"type": "str", "required": True, "secret": True, "desc": "腾讯云 API 密钥 Key"},
                "region": {"type": "str", "required": True, "default": "ap-beijing", "desc": "API 地域 (如 ap-beijing)"}
            }
        }
    
    def handle_click(self):
        self.start_capture()
    
    def start_capture(self):
        """Start screen capture"""
        self._capture_widget = ScreenCaptureWidget()
        self._capture_widget.capture_finished.connect(self.on_capture_finished)
        self._capture_widget.show()
    
    def on_capture_finished(self, rect: QRect):
        """Handle capture finished"""
        try:
            screen = QGuiApplication.primaryScreen()
            screenshot = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
            
            with tempfile.NamedTemporaryFile(prefix="larj_ocr_", suffix=".png", delete=False) as tmp:
                self._temp_image_path = tmp.name
            screenshot.save(self._temp_image_path, "PNG")
            
            self._result_dialog = OcrResultDialog()
            self._result_dialog.show()
            self.do_ocr()
            
        except Exception as e:
            self.logger.error(f"Capture failed: {e}", exc_info=True)
    
    def do_ocr(self):
        """Execute OCR in background worker to avoid blocking UI."""
        if not self._temp_image_path:
            if self._result_dialog:
                self._result_dialog.set_error("截图文件不存在")
            return
        worker = OcrWorker(
            self._secret_id,
            self._secret_key,
            self._region,
            self._temp_image_path,
        )
        self._ocr_worker = worker

        def _on_finished(text_detections: List[Dict]):
            if self._result_dialog:
                self._result_dialog.set_result(text_detections)
            self.cleanup_temp_file()

        def _on_error(error_msg: str):
            if self._result_dialog:
                self._result_dialog.set_error(error_msg)
            self.cleanup_temp_file()

        def _on_worker_done(*_args):
            self._ocr_worker = None

        worker.finished.connect(_on_finished)
        worker.error.connect(_on_error)
        worker.finished.connect(_on_worker_done)
        worker.error.connect(lambda _msg: _on_worker_done())
        worker.start()
    
    def cleanup_temp_file(self):
        """Delete temporary screenshot file"""
        if self._temp_image_path and os.path.exists(self._temp_image_path):
            try:
                os.remove(self._temp_image_path)
                self.logger.debug(f"Deleted temp file: {self._temp_image_path}")
            except Exception as e:
                self.logger.warning(f"Failed to delete temp file: {e}")
            self._temp_image_path = None
    
    def on_load(self):
        self.logger.info("TencentOcr plugin loaded")
    
    def on_unload(self):
        if self._capture_widget:
            self._capture_widget.close()
        if self._result_dialog:
            self._result_dialog.close()
        if self._ocr_worker and self._ocr_worker.isRunning():
            self._ocr_worker.quit()
            self._ocr_worker.wait(1500)
        self._ocr_worker = None
        self.cleanup_temp_file()
        self.logger.info("TencentOcr plugin unloaded")
    
    def get_settings(self) -> dict:
        return {}
    
plugin_class = TencentOcrPlugin
