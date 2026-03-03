#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tencent Translation Plugin - Translation plugin using Tencent Cloud API
Based on Tencent Cloud Machine Translation (TMT) API v3
"""

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from typing import Dict

import requests
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QComboBox, QWidget
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

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


class TranslationWorker(QThread):
    """Worker thread for translation requests"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    LANGUAGES = {
        "自动检测": "auto",
        "简体中文": "zh",
        "繁体中文": "zh-TW",
        "英语": "en",
        "日语": "ja",
        "韩语": "ko",
        "法语": "fr",
        "德语": "de",
        "西班牙语": "es",
        "意大利语": "it",
        "俄语": "ru",
        "葡萄牙语": "pt",
        "越南语": "vi",
        "泰语": "th",
        "阿拉伯语": "ar",
    }
    
    def __init__(self, secret_id: str, secret_key: str, 
                 text: str, source_lang: str, target_lang: str,
                 region: str = "ap-beijing"):
        super().__init__()
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.text = text
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.region = region
    
    def run(self):
        try:
            if not self.secret_id or not self.secret_key:
                self.error.emit("请先配置 SecretId 和 SecretKey")
                return
            
            service = "tmt"
            host = "tmt.tencentcloudapi.com"
            action = "TextTranslate"
            version = "2018-03-21"
            
            payload_dict = {
                "SourceText": self.text,
                "Source": self.source_lang,
                "Target": self.target_lang,
                "ProjectId": 0
            }
            payload = json.dumps(payload_dict)
            
            headers = TencentSigner.sign(
                self.secret_id, self.secret_key,
                service, host, action, version,
                self.region, payload
            )
            
            url = f"https://{host}/"
            response = requests.post(url, headers=headers, data=payload, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                if "Response" in result:
                    if "Error" in result["Response"]:
                        error_msg = result["Response"]["Error"].get("Message", "Unknown error")
                        self.error.emit(f"API错误: {error_msg}")
                    else:
                        translated = result["Response"].get("TargetText", "")
                        self.finished.emit(translated)
                else:
                    self.error.emit("响应格式错误")
            else:
                self.error.emit(f"HTTP错误: {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.error.emit("请求超时")
        except requests.exceptions.ConnectionError:
            self.error.emit("网络连接失败")
        except Exception as e:
            self.error.emit(str(e))


class TranslationDialog(QDialog):
    """Translation dialog UI with modern design"""
    
    LANGUAGES = TranslationWorker.LANGUAGES
    
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.worker = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("腾讯翻译")
        self.setMinimumSize(480, 420)
        self.setWindowFlags(Qt.Dialog)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        title_bar = QWidget()
        title_bar.setFixedHeight(48)
        title_bar.setStyleSheet("background: #f8fafc;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 16, 0)
        
        title_label = QLabel("腾讯翻译")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
            background: transparent;
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748b;
                font-size: 20px;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background: #fee2e2;
                color: #ef4444;
            }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        main_layout.addWidget(title_bar)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background: #ffffff;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(20, 16, 20, 20)
        
        lang_widget = QWidget()
        lang_widget.setStyleSheet("background: transparent;")
        lang_layout = QHBoxLayout(lang_widget)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.setSpacing(8)
        
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(list(self.LANGUAGES.keys()))
        self.source_lang_combo.setCurrentText("自动检测")
        self.source_lang_combo.setStyleSheet(self._get_combo_style())
        lang_layout.addWidget(self.source_lang_combo, 1)
        
        swap_btn = QPushButton("⇄")
        swap_btn.setFixedSize(40, 36)
        swap_btn.setCursor(Qt.PointingHandCursor)
        swap_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #475569;
                font-size: 16px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #e2e8f0;
                color: #3b82f6;
            }
            QPushButton:pressed {
                background: #cbd5e1;
            }
        """)
        swap_btn.clicked.connect(self.swap_languages)
        lang_layout.addWidget(swap_btn)
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(list(self.LANGUAGES.keys()))
        self.target_lang_combo.setCurrentText("简体中文")
        self.target_lang_combo.setStyleSheet(self._get_combo_style())
        lang_layout.addWidget(self.target_lang_combo, 1)
        
        content_layout.addWidget(lang_widget)
        
        self.source_text = QTextEdit()
        self.source_text.setPlaceholderText("输入要翻译的文本...")
        self.source_text.setFixedHeight(100)
        self.source_text.setStyleSheet(self._get_textedit_style())
        self.source_text.textChanged.connect(self._on_text_changed)
        content_layout.addWidget(self.source_text)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.translate_btn = QPushButton("翻译")
        self.translate_btn.setFixedHeight(40)
        self.translate_btn.setCursor(Qt.PointingHandCursor)
        self.translate_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                font-size: 14px;
                font-weight: 500;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: #2563eb;
            }
            QPushButton:pressed {
                background: #1d4ed8;
            }
            QPushButton:disabled {
                background: #94a3b8;
            }
        """)
        self.translate_btn.clicked.connect(self.do_translate)
        btn_layout.addWidget(self.translate_btn, 2)
        
        clear_btn = QPushButton("清空")
        clear_btn.setFixedHeight(40)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #475569;
                font-size: 14px;
                font-weight: 500;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: #e2e8f0;
            }
            QPushButton:pressed {
                background: #cbd5e1;
            }
        """)
        clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(clear_btn, 1)
        
        content_layout.addLayout(btn_layout)
        
        self.result_text = QTextEdit()
        self.result_text.setPlaceholderText("翻译结果...")
        self.result_text.setFixedHeight(100)
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet(self._get_textedit_style(read_only=True))
        content_layout.addWidget(self.result_text)
        
        status_layout = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #64748b; font-size: 12px; background: transparent;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.char_count_label = QLabel("0/6000")
        self.char_count_label.setStyleSheet("color: #94a3b8; font-size: 12px; background: transparent;")
        status_layout.addWidget(self.char_count_label)
        
        content_layout.addLayout(status_layout)
        
        main_layout.addWidget(content_widget)
    
    def _get_combo_style(self):
        return """
            QComboBox {
                padding: 10px 14px;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                background: #ffffff;
                font-size: 13px;
                color: #334155;
            }
            QComboBox:hover {
                border-color: #cbd5e1;
            }
            QComboBox:focus {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #64748b;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                background: #ffffff;
                selection-background-color: #f1f5f9;
                selection-color: #1e293b;
                padding: 4px;
            }
        """
    
    def _get_textedit_style(self, read_only=False):
        bg = "#f8fafc" if not read_only else "#f1f5f9"
        return f"""
            QTextEdit {{
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                padding: 12px;
                font-size: 14px;
                background: {bg};
                color: #1e293b;
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border-color: #3b82f6;
            }}
        """
    
    def _on_text_changed(self):
        text = self.source_text.toPlainText()
        count = len(text)
        self.char_count_label.setText(f"{count}/6000")
        if count > 6000:
            self.char_count_label.setStyleSheet("color: #ef4444; font-size: 12px; background: transparent;")
        else:
            self.char_count_label.setStyleSheet("color: #94a3b8; font-size: 12px; background: transparent;")
    
    def do_translate(self):
        text = self.source_text.toPlainText().strip()
        if not text:
            self.status_label.setText("请输入要翻译的文本")
            return
        
        if len(text) > 6000:
            self.status_label.setText("文本长度超过6000字符限制")
            return
        
        secret_id = self.plugin._secret_id
        secret_key = self.plugin._secret_key
        
        if not secret_id or not secret_key:
            self.status_label.setText("请先配置 SecretId 和 SecretKey")
            return
        
        source_lang = self.LANGUAGES.get(self.source_lang_combo.currentText(), "auto")
        target_lang = self.LANGUAGES.get(self.target_lang_combo.currentText(), "zh")
        
        self.translate_btn.setEnabled(False)
        self.translate_btn.setText("翻译中...")
        self.status_label.setText("")
        
        self.worker = TranslationWorker(
            secret_id, secret_key, text, source_lang, target_lang,
            self.plugin._region
        )
        self.worker.finished.connect(self.on_translation_finished)
        self.worker.error.connect(self.on_translation_error)
        self.worker.start()
    
    def on_translation_finished(self, result):
        self.result_text.setPlainText(result)
        self.status_label.setText("翻译完成")
        self.translate_btn.setText("翻译")
        self.translate_btn.setEnabled(True)
    
    def on_translation_error(self, error_msg):
        self.status_label.setText(f"错误: {error_msg}")
        self.translate_btn.setText("翻译")
        self.translate_btn.setEnabled(True)
    
    def swap_languages(self):
        source_idx = self.source_lang_combo.currentIndex()
        target_idx = self.target_lang_combo.currentIndex()
        
        if source_idx == 0:
            self.status_label.setText("自动检测模式无法交换")
            return
        
        self.source_lang_combo.blockSignals(True)
        self.target_lang_combo.blockSignals(True)
        
        self.source_lang_combo.setCurrentIndex(target_idx)
        self.target_lang_combo.setCurrentIndex(source_idx)
        
        self.source_lang_combo.blockSignals(False)
        self.target_lang_combo.blockSignals(False)
        
        source_text = self.source_text.toPlainText()
        result_text = self.result_text.toPlainText()
        
        if result_text.strip():
            self.source_text.setPlainText(result_text)
            self.result_text.setPlainText(source_text)
        
        self.status_label.setText("")
    
    def clear_all(self):
        self.source_text.clear()
        self.result_text.clear()
        self.status_label.clear()
        self.char_count_label.setText("0/6000")


class TencentTranslationPlugin(PluginBase):
    """Tencent Cloud Translation Plugin"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._secret_id = ""
        self._secret_key = ""
        self._region = "ap-beijing"
        self._dialog = None
    
    def get_metadata(self) -> dict:
        return {
            "plugin_id": "mtran_server",
            "name": "腾讯翻译",
            "icon": "translate",
            "version": "1.0.0",
            "author": "Larj Team",
            "description": "腾讯云机器翻译插件 - 支持多语言翻译",
            "config_schema": {
                "secret_id": {"type": "str", "required": True, "desc": "腾讯云 API 密钥 ID"},
                "secret_key": {"type": "str", "required": True, "secret": True, "desc": "腾讯云 API 密钥 Key"},
                "region": {"type": "str", "required": True, "default": "ap-beijing", "desc": "API 地域 (如 ap-beijing, ap-shanghai)"}
            }
        }
    
    def handle_click(self):
        if self._dialog is None or not self._dialog.isVisible():
            self._dialog = TranslationDialog(self)
            self._dialog.show()
        else:
            self._dialog.raise_()
            self._dialog.activateWindow()
    
    def on_load(self):
        self.logger.info("TencentTranslation plugin loaded")
    
    def on_unload(self):
        if self._dialog:
            self._dialog.close()
        self.logger.info("TencentTranslation plugin unloaded")
    
    def apply_settings(self, settings: dict):
        if "secret_id" in settings:
            self._secret_id = settings["secret_id"]
        if "secret_key" in settings:
            self._secret_key = settings["secret_key"]
        if "region" in settings:
            self._region = settings["region"]


plugin_class = TencentTranslationPlugin
