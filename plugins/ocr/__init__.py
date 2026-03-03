#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tencent OCR Plugin - Screen text recognition using Tencent Cloud OCR API
Click plugin to start area screenshot, then recognize text and display result
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import tempfile
import time
from datetime import datetime
from typing import Dict, List

import requests
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QWidget, QApplication
)
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QGuiApplication

from src.core.plugin_system import PluginBase


class TencentSigner:
    """Tencent Cloud API v3 Signature Generator"""
    
    @staticmethod
    def sha256_hex(s: str) -> str:
        return hashlib.sha256(s.encode('utf-8')).hexdigest()
    
    @staticmethod
    def hmac_sha256(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    
    @classmethod
    def sign(cls, secret_id: str, secret_key: str, 
             service: str, host: str, action: str, 
             version: str, region: str, payload: str) -> Dict[str, str]:
        algorithm = "TC3-HMAC-SHA256"
        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        ct = "application/json; charset=utf-8"
        
        canonical_headers = f"content-type:{ct}\nhost:{host}\nx-tc-action:{action.lower()}\n"
        signed_headers = "content-type;host;x-tc-action"
        hashed_request_payload = cls.sha256_hex(payload)
        
        canonical_request = (
            f"{http_request_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_request_payload}"
        )
        
        credential_scope = f"{date}/{service}/tc3_request"
        hashed_canonical_request = cls.sha256_hex(canonical_request)
        string_to_sign = (
            f"{algorithm}\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{hashed_canonical_request}"
        )
        
        secret_date = cls.hmac_sha256(("TC3" + secret_key).encode('utf-8'), date)
        secret_service = cls.hmac_sha256(secret_date, service)
        secret_signing = cls.hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        authorization = (
            f"{algorithm} "
            f"Credential={secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        
        return {
            "Authorization": authorization,
            "Content-Type": ct,
            "Host": host,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": version,
            "X-TC-Region": region,
        }


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


class TencentOcrPlugin(PluginBase):
    """Tencent Cloud OCR Plugin for screen text recognition"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._secret_id = ""
        self._secret_key = ""
        self._region = "ap-beijing"
        self._capture_widget = None
        self._result_dialog = None
        self._temp_image_path = None
    
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
            
            temp_dir = tempfile.gettempdir()
            self._temp_image_path = os.path.join(temp_dir, "larj_ocr_capture.png")
            screenshot.save(self._temp_image_path, "PNG")
            
            self._result_dialog = OcrResultDialog()
            self._result_dialog.show()
            
            QTimer.singleShot(100, self.do_ocr)
            
        except Exception as e:
            self.logger.error(f"Capture failed: {e}", exc_info=True)
    
    def do_ocr(self):
        """Execute OCR using Tencent Cloud API"""
        try:
            if not self._secret_id or not self._secret_key:
                self._result_dialog.set_error("请先在设置中配置 SecretId 和 SecretKey")
                return
            
            with open(self._temp_image_path, "rb") as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            service = "ocr"
            host = "ocr.tencentcloudapi.com"
            action = "GeneralAccurateOCR"
            version = "2018-11-19"
            
            payload_dict = {
                "ImageBase64": image_base64
            }
            payload = json.dumps(payload_dict)
            
            headers = TencentSigner.sign(
                self._secret_id, self._secret_key,
                service, host, action, version,
                self._region, payload
            )
            
            url = f"https://{host}/"
            response = requests.post(url, headers=headers, data=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if "Response" in result:
                    if "Error" in result["Response"]:
                        error_msg = result["Response"]["Error"].get("Message", "Unknown error")
                        self._result_dialog.set_error(f"API错误: {error_msg}")
                    else:
                        text_detections = result["Response"].get("TextDetections", [])
                        self._result_dialog.set_result(text_detections)
                else:
                    self._result_dialog.set_error("响应格式错误")
            else:
                self._result_dialog.set_error(f"HTTP错误: {response.status_code}")
                
        except requests.exceptions.Timeout:
            self._result_dialog.set_error("请求超时")
        except requests.exceptions.ConnectionError:
            self._result_dialog.set_error("网络连接失败")
        except Exception as e:
            self._result_dialog.set_error(f"识别失败: {e}")
        finally:
            self.cleanup_temp_file()
    
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
        self.cleanup_temp_file()
        self.logger.info("TencentOcr plugin unloaded")
    
    def apply_settings(self, settings: dict):
        if "secret_id" in settings:
            self._secret_id = settings["secret_id"]
        if "secret_key" in settings:
            self._secret_key = settings["secret_key"]
        if "region" in settings:
            self._region = settings["region"]


plugin_class = TencentOcrPlugin
