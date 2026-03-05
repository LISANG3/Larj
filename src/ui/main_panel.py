#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Panel - The main UI window
Contains search box, app grid, and search results
"""

import logging
import os
import struct
from pathlib import Path
import psutil
from PyQt5.QtWidgets import (
    QWidget, QApplication, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QScrollArea, QLabel, QGridLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QFrame, QDialog, QDialogButtonBox, QFormLayout,
    QCheckBox, QSpinBox, QFileDialog, QMessageBox, QGraphicsDropShadowEffect,
    QMenu, QAction, QInputDialog, QColorDialog, QComboBox, QToolButton
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QMimeData, QPoint, QSize
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPalette, QLinearGradient, QBrush, QPainter, QPen, QDrag
from pynput import mouse
from src.core.hotkey_listener import detect_hotkey, DEFAULT_TRIGGER_KEY


def extract_icon_from_file(file_path: str, size: int = 48) -> QIcon:
    """Extract icon from executable or shortcut file (Windows)"""
    if not os.path.exists(file_path):
        return QIcon()
    
    ext = Path(file_path).suffix.lower()
    
    if os.name == 'nt':
        try:
            import win32api
            import win32gui
            import win32ui
            import win32con
            
            if ext == '.lnk':
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(file_path)
                target_path = shortcut.Targetpath
                if target_path and os.path.exists(target_path):
                    file_path = target_path
                    ext = Path(target_path).suffix.lower()
            
            if ext in ['.exe', '.dll', '.ico']:
                hicon = win32gui.ExtractIcon(0, file_path, 0)
                if hicon > 0:
                    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                    hbmp = win32ui.CreateBitmap()
                    hbmp.CreateCompatibleBitmap(hdc, size, size)
                    hdc_mem = hdc.CreateCompatibleDC()
                    hdc_mem.SelectObject(hbmp)
                    hdc_mem.DrawIcon((0, 0), hicon)
                    
                    bmpinfo = hbmp.GetInfo()
                    bmpstr = hbmp.GetBitmapBits(True)
                    
                    from PyQt5.QtGui import QImage
                    img = QImage(bmpstr, bmpinfo['bmWidth'], bmpinfo['bmHeight'], QImage.Format_ARGB32)
                    pixmap = QPixmap.fromImage(img)
                    
                    win32gui.DestroyIcon(hicon)
                    return QIcon(pixmap)
        except ImportError:
            pass
        except Exception:
            pass
    
    if os.path.isdir(file_path):
        return QIcon.fromTheme("folder", QIcon())
    
    return QIcon.fromTheme("application-x-executable", QIcon())


class ModernStyle:
    # ── Accent color tokens (can be overridden at runtime) ─────────
    ACCENT = "#6366f1"          # Indigo-500
    ACCENT_HOVER = "#4f46e5"    # Indigo-600
    ACCENT_LIGHT = "#eef2ff"    # Indigo-50
    ACCENT_MUTED = "#a5b4fc"    # Indigo-300

    MODERN_STYLE = """
    QWidget#mainPanel {
        border-radius: 18px;
        border: 1px solid rgba(148, 163, 184, 0.25);
    }

    QLineEdit#searchBox {
        padding: 14px 18px 14px 42px;
        font-size: 14px;
        font-family: "Segoe UI Variable", "Microsoft YaHei UI", "PingFang SC", sans-serif;
        border: 1.5px solid rgba(148, 163, 184, 0.3);
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.85);
        color: #0f172a;
        selection-background-color: #6366f1;
    }

    QLineEdit#searchBox:focus {
        border-color: #6366f1;
        background: #ffffff;
    }

    QLineEdit#searchBox::placeholder {
        color: #94a3b8;
    }

    QPushButton#settingsBtn {
        padding: 0px;
        font-size: 18px;
        border: none;
        border-radius: 12px;
        background: rgba(241, 245, 249, 0.8);
        color: #64748b;
    }

    QPushButton#settingsBtn:hover {
        background: #eef2ff;
        color: #6366f1;
    }

    QPushButton#settingsBtn:pressed {
        background: #e0e7ff;
    }

    QScrollArea {
        border: none;
        background: transparent;
    }

    QScrollBar:vertical {
        background: transparent;
        width: 5px;
        margin: 6px 1px;
        border-radius: 2px;
    }

    QScrollBar::handle:vertical {
        background: rgba(148, 163, 184, 0.4);
        border-radius: 2px;
        min-height: 36px;
    }

    QScrollBar::handle:vertical:hover {
        background: rgba(100, 116, 139, 0.55);
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }

    QListWidget {
        border: none;
        background: transparent;
        outline: none;
    }

    QListWidget::item {
        padding: 10px 14px;
        border-radius: 10px;
        margin: 2px 4px;
        background: transparent;
        color: #334155;
        font-family: "Segoe UI Variable", "Microsoft YaHei UI", sans-serif;
        font-size: 13px;
    }

    QListWidget::item:hover {
        background: rgba(99, 102, 241, 0.06);
    }

    QListWidget::item:selected {
        background: #6366f1;
        color: #ffffff;
    }

    QLabel#memoryLabel {
        color: #94a3b8;
        font-size: 10px;
        font-family: "Segoe UI Variable", "Microsoft YaHei UI", sans-serif;
        padding: 3px 10px;
        background: rgba(241, 245, 249, 0.6);
        border-radius: 8px;
    }

    QLabel#hintLabel {
        color: #a5b4fc;
        font-size: 10px;
        font-family: "Segoe UI Variable", "Microsoft YaHei UI", sans-serif;
        padding: 3px 0px;
    }
    """

    APP_BUTTON_STYLE = """
    QToolButton {
        font-size: 11px;
        font-family: "Segoe UI Variable", "Microsoft YaHei UI", "PingFang SC", sans-serif;
        font-weight: 500;
        border: none;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.92);
        color: #475569;
        padding: 12px 8px 8px 8px;
        margin: 4px;
    }

    QToolButton:hover {
        background: #ffffff;
        border: 2px solid #6366f1;
        color: #4f46e5;
        padding: 10px 6px 6px 6px;
    }

    QToolButton:pressed {
        background: #eef2ff;
        border: 2px solid #818cf8;
        color: #4338ca;
    }
    """

    ADD_BUTTON_STYLE = """
    QPushButton {
        padding: 14px;
        font-size: 12px;
        font-family: "Segoe UI Variable", "Microsoft YaHei UI", "PingFang SC", sans-serif;
        font-weight: 500;
        border: 1.5px dashed rgba(165, 180, 252, 0.5);
        border-radius: 14px;
        background: rgba(238, 242, 255, 0.35);
        color: #818cf8;
    }

    QPushButton:hover {
        background: rgba(238, 242, 255, 0.7);
        border-color: #6366f1;
        color: #6366f1;
    }
    """

    DIALOG_STYLE = """
    QDialog {
        background: #ffffff;
        border-radius: 18px;
    }

    QLabel {
        font-family: "Segoe UI Variable", "Microsoft YaHei UI", "PingFang SC", sans-serif;
        font-size: 13px;
        color: #334155;
    }

    QLineEdit {
        padding: 10px 14px;
        font-size: 13px;
        border: 1.5px solid #e2e8f0;
        border-radius: 10px;
        background: #f8fafc;
        color: #0f172a;
    }

    QLineEdit:focus {
        border-color: #6366f1;
        background: #ffffff;
    }

    QCheckBox {
        font-family: "Segoe UI Variable", "Microsoft YaHei UI", "PingFang SC", sans-serif;
        font-size: 13px;
        color: #334155;
        spacing: 8px;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1.5px solid #cbd5e1;
        background: #ffffff;
    }

    QCheckBox::indicator:checked {
        background: #6366f1;
        border-color: #6366f1;
    }

    QSpinBox {
        padding: 8px 12px;
        font-size: 13px;
        border: 1.5px solid #e2e8f0;
        border-radius: 10px;
        background: #f8fafc;
        color: #0f172a;
    }

    QSpinBox:focus {
        border-color: #6366f1;
    }

    QPushButton {
        padding: 10px 20px;
        font-size: 13px;
        font-family: "Segoe UI Variable", "Microsoft YaHei UI", "PingFang SC", sans-serif;
        font-weight: 500;
        border: none;
        border-radius: 10px;
    }

    QPushButton#detectBtn {
        background: #f1f5f9;
        color: #475569;
    }

    QPushButton#detectBtn:hover {
        background: #eef2ff;
        color: #6366f1;
    }
    """


class MainPanel(QWidget):
    """
    Main panel window - the floating panel UI
    """
    
    app_clicked = pyqtSignal(dict)
    search_changed = pyqtSignal(str)
    MEMORY_PLACEHOLDER = "-- MB"
    MEMORY_UPDATE_INTERVAL_MS = 2000
    
    def __init__(self, config_manager, search_engine, application_manager, plugin_system):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.search_engine = search_engine
        self.application_manager = application_manager
        self.plugin_system = plugin_system
        self._settings_dialog = None
        self._mouse_listener = None
        self._bg_pixmap_cache = None  # ((path, width, height), scaled_pixmap)
        
        self._setup_ui()
        self._connect_signals()
        self._load_apps()
        self._start_mouse_listener()
        
        self.logger.info("MainPanel initialized")
    
    def _setup_ui(self):
        """Setup the user interface"""
        self.setObjectName("mainPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 12)
        layout.setSpacing(14)

        # ── Header: search box + settings gear ────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Search box with search icon drawn via paintEvent overlay
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("🔍  搜索文件或输入命令…")
        self.search_box.setMinimumHeight(46)
        header_layout.addWidget(self.search_box, 1)

        self.settings_button = QPushButton("⚙")
        self.settings_button.setObjectName("settingsBtn")
        self.settings_button.setFixedSize(46, 46)
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.setToolTip("设置")
        self.settings_button.setAccessibleName("设置")
        self.settings_button.clicked.connect(self._on_settings_clicked)
        header_layout.addWidget(self.settings_button)
        layout.addLayout(header_layout)

        # ── Stacked pages: app grid / search results ──────────────────
        self.stacked_widget = QStackedWidget()

        # -- App grid page --
        self.app_grid_widget = QWidget()
        self.app_grid_widget.setStyleSheet("background: transparent;")
        self.app_grid_layout = QVBoxLayout(self.app_grid_widget)
        self.app_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.app_grid_layout.setSpacing(10)

        app_scroll = QScrollArea()
        app_scroll.setWidgetResizable(True)
        app_scroll.setFrameShape(QFrame.NoFrame)
        app_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        app_scroll.setStyleSheet("background: transparent;")

        app_container = QWidget()
        app_container.setStyleSheet("background: transparent;")
        self.app_grid = QGridLayout(app_container)
        self.app_grid.setSpacing(10)
        self.app_grid.setContentsMargins(2, 2, 2, 2)
        app_scroll.setWidget(app_container)

        self.app_grid_layout.addWidget(app_scroll)

        self.add_app_button = QPushButton("+ 添加应用")
        self.add_app_button.setStyleSheet(ModernStyle.ADD_BUTTON_STYLE)
        self.add_app_button.setMinimumHeight(46)
        self.add_app_button.setCursor(Qt.PointingHandCursor)
        self.add_app_button.clicked.connect(self._on_add_app_clicked)
        self.app_grid_layout.addWidget(self.add_app_button)

        # -- Search results page --
        self.search_results_widget = QWidget()
        self.search_results_widget.setStyleSheet("background: transparent;")
        search_results_layout = QVBoxLayout(self.search_results_widget)
        search_results_layout.setContentsMargins(0, 0, 0, 0)

        self.search_results = QListWidget()
        self.search_results.setStyleSheet("""
            QListWidget {
                border: none;
                background: transparent;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-radius: 10px;
                margin: 2px 4px;
                background: transparent;
                color: #334155;
                font-family: "Segoe UI Variable", "Microsoft YaHei UI", sans-serif;
                font-size: 13px;
            }
            QListWidget::item:hover {
                background: rgba(99, 102, 241, 0.06);
            }
            QListWidget::item:selected {
                background: #6366f1;
                color: #ffffff;
            }
        """)
        self.search_results.setSpacing(1)
        self.search_results.itemDoubleClicked.connect(self._on_search_result_clicked)
        search_results_layout.addWidget(self.search_results)

        self.stacked_widget.addWidget(self.app_grid_widget)
        self.stacked_widget.addWidget(self.search_results_widget)

        layout.addWidget(self.stacked_widget)

        # ── Footer ────────────────────────────────────────────────────
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(4, 0, 4, 0)
        self.hint_label = QLabel("Esc 隐藏  ·  双击打开文件")
        self.hint_label.setObjectName("hintLabel")
        footer_layout.addWidget(self.hint_label)
        footer_layout.addStretch()
        self.memory_label = QLabel(f"内存: {self.MEMORY_PLACEHOLDER}")
        self.memory_label.setObjectName("memoryLabel")
        footer_layout.addWidget(self.memory_label)
        layout.addLayout(footer_layout)

        self._memory_timer = QTimer(self)
        self._memory_timer.timeout.connect(self._update_memory_usage)
        self._memory_timer.start(self.MEMORY_UPDATE_INTERVAL_MS)
        self._update_memory_usage()

        self.setStyleSheet(ModernStyle.MODERN_STYLE)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(shadow)
    
    def _connect_signals(self):
        """Connect UI signals"""
        self.search_box.textChanged.connect(self._on_search_changed)
        self.search_engine.search_completed.connect(self.update_search_results)
    
    def _on_search_changed(self, text: str):
        """Handle search box text change"""
        if text.strip():
            self.stacked_widget.setCurrentWidget(self.search_results_widget)
            self.search_engine.search(text)
        else:
            self.stacked_widget.setCurrentWidget(self.app_grid_widget)
    
    def _load_apps(self):
        """Load applications and plugins into grid"""
        try:
            for i in reversed(range(self.app_grid.count())):
                item = self.app_grid.itemAt(i)
                if item and item.widget():
                    item.widget().setParent(None)
            
            apps = self.application_manager.get_apps()
            
            all_items = list(apps)
            
            if self.plugin_system:
                for plugin_id, plugin in self.plugin_system.plugins.items():
                    metadata = plugin.get_metadata()
                    all_items.append({
                        "name": metadata.get("name", plugin_id),
                        "type": "plugin",
                        "plugin_instance": plugin
                    })
            
            cols = 4
            for i, item in enumerate(all_items):
                row = i // cols
                col = i % cols
                
                if item.get("type") == "plugin":
                    button = self._create_plugin_button(item)
                else:
                    button = self._create_app_button(item)
                self.app_grid.addWidget(button, row, col)
            
            self.logger.debug(f"Loaded {len(apps)} apps and {len(all_items) - len(apps)} plugins")
            
        except Exception as e:
            self.logger.error(f"Failed to load apps: {e}", exc_info=True)
    
    def _create_plugin_button(self, plugin_item: dict) -> QToolButton:
        """Create a button for a plugin with icon on top and name below"""
        plugin = plugin_item.get("plugin_instance")
        metadata = plugin.get_metadata()

        button = QToolButton()
        button.setText(metadata.get("name", "Plugin"))
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        button.setFixedSize(100, 100)
        button.setStyleSheet(ModernStyle.APP_BUTTON_STYLE)
        button.setCursor(Qt.PointingHandCursor)

        button.setProperty("plugin_data", plugin_item)
        button.clicked.connect(lambda: self._on_plugin_clicked(plugin))

        font = QFont("Segoe UI Variable", 10, QFont.Normal)
        button.setFont(font)

        default_icon = self._create_default_plugin_icon(metadata.get("name", "Plugin"))
        button.setIcon(default_icon)
        button.setIconSize(QSize(40, 40))

        return button

    def _create_default_plugin_icon(self, name: str) -> QIcon:
        """Create a default icon for plugins based on name"""
        colors = [
            QColor(99, 102, 241),
            QColor(139, 92, 246),
            QColor(59, 130, 246),
            QColor(16, 185, 129),
            QColor(245, 158, 11),
        ]
        color = colors[hash(name) % len(colors)]
        
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
        
        painter.setPen(QPen(QColor(255, 255, 255), 2.5))
        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x0084, name[0].upper() if name else "P")
        painter.end()
        
        return QIcon(pixmap)
    
    def _on_plugin_clicked(self, plugin):
        """Handle plugin button click"""
        try:
            if self.plugin_system:
                self.plugin_system.handle_plugin_click(plugin)
        except Exception as e:
            self.logger.error(f"Failed to handle plugin click: {e}", exc_info=True)
    
    def _create_app_button(self, app: dict) -> QToolButton:
        """Create a button for an app with icon on top and name below"""
        button = QToolButton()
        button.setText(app.get("name", "Unknown"))
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        button.setFixedSize(100, 100)
        button.setStyleSheet(ModernStyle.APP_BUTTON_STYLE)
        button.setCursor(Qt.PointingHandCursor)
        
        button.setProperty("app_data", app)
        button.clicked.connect(lambda: self._on_app_clicked(app))
        
        icon = extract_icon_from_file(app.get("path", ""))
        if not icon.isNull():
            button.setIcon(icon)
            button.setIconSize(QSize(40, 40))
        else:
            default_icon = self._create_default_app_icon(app.get("name", "App"))
            button.setIcon(default_icon)
            button.setIconSize(QSize(40, 40))
        
        font = QFont("Segoe UI Variable", 10, QFont.Normal)
        button.setFont(font)
        
        button.setContextMenuPolicy(Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(lambda pos, b=button, a=app: self._show_app_context_menu(pos, b, a))
        
        button.setAcceptDrops(True)
        button.drag_start_pos = None
        
        return button

    def _create_default_app_icon(self, name: str) -> QIcon:
        """Create a default icon for apps based on name"""
        colors = [
            QColor(99, 102, 241),
            QColor(139, 92, 246),
            QColor(59, 130, 246),
            QColor(16, 185, 129),
            QColor(245, 158, 11),
            QColor(239, 68, 68),
            QColor(236, 72, 153),
        ]
        color = colors[hash(name) % len(colors)]
        
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
        
        painter.setPen(QPen(QColor(255, 255, 255), 2.5))
        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x0084, name[0].upper() if name else "A")
        painter.end()
        
        return QIcon(pixmap)
    
    def _show_app_context_menu(self, pos, button, app):
        """Show context menu for app button"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid rgba(148, 163, 184, 0.25);
                border-radius: 10px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 20px 8px 14px;
                border-radius: 6px;
                color: #334155;
                font-family: "Segoe UI Variable", "Microsoft YaHei UI", sans-serif;
                font-size: 13px;
            }
            QMenu::item:selected {
                background: rgba(99, 102, 241, 0.08);
                color: #4f46e5;
            }
            QMenu::separator {
                height: 1px;
                background: #f1f5f9;
                margin: 4px 8px;
            }
        """)
        
        edit_action = menu.addAction("✏️  编辑")
        edit_action.triggered.connect(lambda: self._edit_app(app))

        rename_action = menu.addAction("📝  重命名")
        rename_action.triggered.connect(lambda: self._rename_app(app))
        
        delete_action = menu.addAction("🗑️  删除")
        delete_action.triggered.connect(lambda: self._delete_app(app))
        
        menu.addSeparator()
        
        move_up_action = menu.addAction("⬆  上移")
        move_up_action.triggered.connect(lambda: self._move_app(app, -1))
        
        move_down_action = menu.addAction("⬇  下移")
        move_down_action.triggered.connect(lambda: self._move_app(app, 1))
        
        menu.exec_(button.mapToGlobal(pos))
    
    def _edit_app(self, app: dict):
        """Edit application"""
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑应用")
        dialog.setModal(True)
        dialog.setMinimumWidth(380)
        dialog.setStyleSheet(ModernStyle.DIALOG_STYLE)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        name_input = QLineEdit()
        name_input.setText(app.get("name", ""))
        form_layout.addRow("名称:", name_input)
        
        path_input = QLineEdit()
        path_input.setText(app.get("path", ""))
        path_input.setReadOnly(True)
        form_layout.addRow("路径:", path_input)
        
        args_input = QLineEdit()
        args_input.setText(app.get("args", ""))
        form_layout.addRow("参数:", args_input)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_() == QDialog.Accepted:
            new_name = name_input.text().strip()
            new_args = args_input.text().strip()
            
            if new_name:
                updated_app = app.copy()
                updated_app["name"] = new_name
                updated_app["args"] = new_args
                self.application_manager.update_app(app.get("id"), updated_app)
                self._load_apps()

    def _rename_app(self, app: dict):
        """Quickly rename an application icon"""
        new_name, ok = QInputDialog.getText(
            self, "重命名", "请输入新名称:", text=app.get("name", "")
        )
        if ok and new_name.strip():
            updated_app = app.copy()
            updated_app["name"] = new_name.strip()
            self.application_manager.update_app(app.get("id"), updated_app)
            self._load_apps()

    def _delete_app(self, app: dict):
        """Delete application"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 '{app.get('name')}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.application_manager.remove_app(app.get("id"))
            self._load_apps()
    
    def _move_app(self, app: dict, direction: int):
        """Move app up or down in the list"""
        apps = self.config_manager.get_apps()
        app_id = app.get("id")
        
        current_index = -1
        for i, a in enumerate(apps):
            if a.get("id") == app_id:
                current_index = i
                break
        
        if current_index == -1:
            return
        
        new_index = current_index + direction
        if new_index < 0 or new_index >= len(apps):
            return
        
        apps[current_index], apps[new_index] = apps[new_index], apps[current_index]
        self.config_manager.save_apps()
        self._load_apps()
    
    def _on_app_clicked(self, app: dict):
        """Handle app button click"""
        try:
            self.application_manager.launch_app(app)
            self.hide()
        except Exception as e:
            self.logger.error(f"Failed to launch app: {e}", exc_info=True)
    
    def _on_add_app_clicked(self):
        """Handle add app button click"""
        try:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background: #ffffff;
                    border: 1px solid rgba(148, 163, 184, 0.25);
                    border-radius: 10px;
                    padding: 6px;
                }
                QMenu::item {
                    padding: 8px 20px 8px 14px;
                    border-radius: 6px;
                    color: #334155;
                    font-family: "Segoe UI Variable", "Microsoft YaHei UI", sans-serif;
                    font-size: 13px;
                }
                QMenu::item:selected {
                    background: rgba(99, 102, 241, 0.08);
                    color: #4f46e5;
                }
            """)
            
            add_app_action = menu.addAction("📦  添加应用程序")
            add_folder_action = menu.addAction("📂  添加文件夹")
            
            action = menu.exec_(self.add_app_button.mapToGlobal(QPoint(0, -50)))
            
            if action == add_app_action:
                file_filter = "Applications (*.exe *.bat *.cmd *.lnk);;All Files (*)" if os.name == "nt" else "All Files (*)"
                file_path, _ = QFileDialog.getOpenFileName(self, "选择应用程序", "", file_filter)
                if file_path:
                    app_name = Path(file_path).stem
                    self.application_manager.add_app(app_name, file_path)
                    self._load_apps()
                    self.logger.info(f"Added app: {app_name}")
                    
            elif action == add_folder_action:
                folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
                if folder_path:
                    folder_name = Path(folder_path).name
                    app_data = {
                        "id": str(__import__('uuid').uuid4()),
                        "name": folder_name,
                        "path": folder_path,
                        "icon_path": "",
                        "args": "",
                        "is_folder": True,
                        "usage_count": 0,
                        "created_at": __import__('datetime').datetime.now().isoformat(),
                        "last_used": None
                    }
                    self.config_manager.add_app(app_data)
                    self._load_apps()
                    self.logger.info(f"Added folder: {folder_name}")
                    
        except Exception as e:
            self.logger.error(f"Failed to add: {e}", exc_info=True)
            QMessageBox.warning(self, "添加失败", str(e))

    def _on_settings_clicked(self):
        """Open settings dialog with tabs"""
        from PyQt5.QtWidgets import QTabWidget, QScrollArea
        
        dialog = QDialog(self)
        self._settings_dialog = dialog
        dialog.setWindowTitle("设置")
        dialog.setModal(True)
        dialog.setMinimumSize(520, 520)
        dialog.setStyleSheet(ModernStyle.DIALOG_STYLE)
        
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #ffffff;
            }
            QTabBar::tab {
                padding: 12px 28px;
                margin: 0;
                background: #f8fafc;
                color: #64748b;
                border: none;
                border-bottom: 2px solid transparent;
                font-family: "Segoe UI Variable", "Microsoft YaHei UI", sans-serif;
                font-size: 13px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #6366f1;
                border-bottom: 2.5px solid #6366f1;
            }
            QTabBar::tab:hover:!selected {
                background: #eef2ff;
                color: #6366f1;
            }
        """)
        
        general_widget = QWidget()
        general_layout = QVBoxLayout(general_widget)
        general_layout.setSpacing(16)
        general_layout.setContentsMargins(24, 24, 24, 24)
        
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(16)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        hotkey_enabled_checkbox = QCheckBox()
        hotkey_enabled_checkbox.setChecked(self.config_manager.get("hotkey.enabled", True))
        form_layout.addRow("启用热键", hotkey_enabled_checkbox)
        
        hotkey_widget = QWidget()
        hotkey_layout = QHBoxLayout(hotkey_widget)
        hotkey_layout.setContentsMargins(0, 0, 0, 0)
        hotkey_layout.setSpacing(8)
        hotkey_input = QLineEdit()
        hotkey_input.setMinimumWidth(150)
        hotkey_input.setText(self.config_manager.get("hotkey.trigger_key", DEFAULT_TRIGGER_KEY))
        detect_hotkey_button = QPushButton("检测")
        detect_hotkey_button.setFixedWidth(60)
        hotkey_layout.addWidget(hotkey_input)
        hotkey_layout.addWidget(detect_hotkey_button)
        form_layout.addRow("触发热键", hotkey_widget)
        
        def on_detect_hotkey():
            dialog.setWindowTitle("设置（按下任意键或鼠标键）")
            detected = detect_hotkey()
            if detected:
                hotkey_input.setText(detected)
            dialog.setWindowTitle("设置")
        
        detect_hotkey_button.clicked.connect(on_detect_hotkey)
        
        follow_mouse_checkbox = QCheckBox()
        follow_mouse_checkbox.setChecked(self.config_manager.get("window.follow_mouse", True))
        form_layout.addRow("窗口跟随鼠标", follow_mouse_checkbox)
        
        hide_on_focus_loss_checkbox = QCheckBox()
        hide_on_focus_loss_checkbox.setChecked(self.config_manager.get("window.hide_on_focus_loss", True))
        form_layout.addRow("点击外部自动隐藏", hide_on_focus_loss_checkbox)
        
        max_results_spinbox = QSpinBox()
        max_results_spinbox.setRange(10, 500)
        max_results_spinbox.setValue(self.config_manager.get("search.max_results", 50))
        max_results_spinbox.setMinimumWidth(100)
        form_layout.addRow("搜索结果上限", max_results_spinbox)
        
        autostart_checkbox = QCheckBox()
        autostart_checkbox.setChecked(self._is_autostart_enabled())
        form_layout.addRow("开机自启动", autostart_checkbox)
        
        general_layout.addWidget(form_widget)
        general_layout.addStretch()
        
        tab_widget.addTab(general_widget, "通用设置")
        
        plugin_widget = QWidget()
        plugin_layout = QVBoxLayout(plugin_widget)
        plugin_layout.setSpacing(16)
        plugin_layout.setContentsMargins(24, 24, 24, 24)
        
        plugin_settings_widgets = {}
        plugin_enable_checkboxes = {}
        
        discovered = self.plugin_system.get_discovered_plugins() if self.plugin_system else {}
        enabled_plugins = self.config_manager.get("plugin.enabled_plugins", [])
        
        if discovered:
            for plugin_id, metadata in discovered.items():
                plugin_group = QWidget()
                plugin_group.setStyleSheet("""
                    QWidget {
                        background: #f8fafc;
                        border-radius: 14px;
                        border: 1px solid rgba(148, 163, 184, 0.2);
                    }
                """)
                group_layout = QVBoxLayout(plugin_group)
                group_layout.setSpacing(12)
                group_layout.setContentsMargins(16, 16, 16, 16)
                
                header_layout = QHBoxLayout()
                
                enable_checkbox = QCheckBox()
                enable_checkbox.setChecked(plugin_id in enabled_plugins)
                enable_checkbox.setStyleSheet("background: transparent;")
                header_layout.addWidget(enable_checkbox)
                plugin_enable_checkboxes[plugin_id] = enable_checkbox
                
                name_label = QLabel(metadata.get("name", plugin_id))
                name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #0f172a; background: transparent;")
                header_layout.addWidget(name_label)
                
                version_label = QLabel(f"v{metadata.get('version', '1.0')}")
                version_label.setStyleSheet("font-size: 11px; color: #a5b4fc; background: transparent; font-weight: 500;")
                header_layout.addWidget(version_label)
                header_layout.addStretch()
                
                group_layout.addLayout(header_layout)
                
                desc_label = QLabel(metadata.get("description", ""))
                desc_label.setStyleSheet("font-size: 12px; color: #64748b; background: transparent;")
                desc_label.setWordWrap(True)
                group_layout.addWidget(desc_label)
                
                config_schema = metadata.get("config_schema", {})
                if config_schema:
                    plugin_settings_widgets[plugin_id] = {}
                    
                    # Load saved config for this plugin
                    saved_config = self.plugin_system.get_plugin_config(plugin_id) if self.plugin_system else {}
                    
                    settings_form = QWidget()
                    settings_form.setStyleSheet("background: transparent;")
                    settings_layout = QFormLayout(settings_form)
                    settings_layout.setSpacing(10)
                    settings_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    settings_layout.setContentsMargins(0, 8, 0, 0)
                    
                    for setting_key, schema in config_schema.items():
                        setting_type = schema.get("type", "str")
                        label = schema.get("desc", setting_key)
                        default_value = schema.get("default", "")
                        
                        saved_value = saved_config.get(setting_key, default_value)
                        
                        widget = QLineEdit()
                        # Use password mode if schema declares secret: true
                        if schema.get("secret", False):
                            widget.setEchoMode(QLineEdit.Password)
                        widget.setText(str(saved_value))
                        widget.setMinimumWidth(200)
                        widget.setStyleSheet("background: #ffffff; border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 8px; padding: 6px 10px;")
                        
                        settings_layout.addRow(label + ":", widget)
                        plugin_settings_widgets[plugin_id][setting_key] = widget
                    
                    group_layout.addWidget(settings_form)
                
                plugin_layout.addWidget(plugin_group)
        else:
            no_plugin_label = QLabel("暂无已加载的插件")
            no_plugin_label.setStyleSheet("color: #94a3b8; font-size: 14px;")
            no_plugin_label.setAlignment(Qt.AlignCenter)
            plugin_layout.addWidget(no_plugin_label)
        
        plugin_layout.addStretch()
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(plugin_widget)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: #ffffff; }")
        
        tab_widget.addTab(scroll_area, "插件管理")

        # ── Appearance tab ────────────────────────────────────────────────────
        appearance_widget = QWidget()
        appearance_layout = QVBoxLayout(appearance_widget)
        appearance_layout.setSpacing(20)
        appearance_layout.setContentsMargins(24, 24, 24, 24)

        # -- Background type ---
        bg_type_label = QLabel("背景类型")
        bg_type_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #0f172a;")
        appearance_layout.addWidget(bg_type_label)

        bg_type_combo = QComboBox()
        bg_type_combo.addItem("纯色", "solid")
        bg_type_combo.addItem("图片", "image")
        current_bg_type = self.config_manager.get("appearance.background_type", "solid")
        for idx in range(bg_type_combo.count()):
            if bg_type_combo.itemData(idx) == current_bg_type:
                bg_type_combo.setCurrentIndex(idx)
                break
        bg_type_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px; font-size: 13px; border: 1.5px solid #e2e8f0;
                border-radius: 10px; background: #f8fafc; color: #0f172a;
            }
            QComboBox:focus { border-color: #6366f1; }
            QComboBox::drop-down { border: none; }
        """)
        appearance_layout.addWidget(bg_type_combo)

        def _make_color_btn(config_key: str, default: str) -> QPushButton:
            color = self.config_manager.get(config_key, default)
            btn = QPushButton()
            btn.setFixedSize(100, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"background: {color}; border: 1.5px solid rgba(148, 163, 184, 0.3); border-radius: 8px;")
            btn.setProperty("color_value", color)

            def pick(checked=False, b=btn, key=config_key):
                current = QColor(b.property("color_value"))
                chosen = QColorDialog.getColor(current, dialog, "选择颜色")
                if chosen.isValid():
                    hex_color = chosen.name()
                    b.setProperty("color_value", hex_color)
                    b.setStyleSheet(f"background: {hex_color}; border: 1.5px solid rgba(148, 163, 184, 0.3); border-radius: 8px;")

            btn.clicked.connect(pick)
            return btn

        # -- Solid color --
        solid_widget = QWidget()
        solid_layout = QFormLayout(solid_widget)
        solid_layout.setSpacing(12)
        solid_layout.setContentsMargins(0, 0, 0, 0)
        solid_color_btn = _make_color_btn("appearance.background_color", "#f8fafc")
        solid_layout.addRow("背景颜色:", solid_color_btn)
        appearance_layout.addWidget(solid_widget)

        # -- Image picker --
        image_widget = QWidget()
        image_layout = QHBoxLayout(image_widget)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(8)
        image_path_input = QLineEdit()
        image_path_input.setText(self.config_manager.get("appearance.background_image", ""))
        image_path_input.setReadOnly(True)
        image_path_input.setPlaceholderText("选择图片文件…")
        image_path_input.setStyleSheet("padding: 8px 12px; font-size: 13px; border: 1.5px solid #e2e8f0; border-radius: 10px;")
        browse_btn = QPushButton("浏览")
        browse_btn.setFixedSize(70, 36)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(
            "QPushButton { background: #f1f5f9; color: #475569; border: none; border-radius: 10px; font-size: 13px; }"
            "QPushButton:hover { background: #eef2ff; color: #6366f1; }"
        )

        def pick_image():
            path, _ = QFileDialog.getOpenFileName(
                dialog, "选择背景图片", "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)"
            )
            if path:
                image_path_input.setText(path)

        browse_btn.clicked.connect(pick_image)
        image_layout.addWidget(image_path_input)
        image_layout.addWidget(browse_btn)
        appearance_layout.addWidget(image_widget)

        # -- Accent color --
        accent_label = QLabel("主题强调色")
        accent_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #0f172a; margin-top: 8px;")
        appearance_layout.addWidget(accent_label)
        accent_color_btn = _make_color_btn("appearance.accent_color", "#6366f1")
        appearance_layout.addWidget(accent_color_btn)

        # Show/hide sub-sections based on bg_type_combo selection
        def _update_appearance_sections(index=None):
            selected = bg_type_combo.currentData()
            solid_widget.setVisible(selected == "solid")
            image_widget.setVisible(selected == "image")

        bg_type_combo.currentIndexChanged.connect(_update_appearance_sections)
        _update_appearance_sections()

        appearance_layout.addStretch()
        tab_widget.addTab(appearance_widget, "外观")
        # ── end Appearance tab ───────────────────────────────────────────────

        main_layout.addWidget(tab_widget)
        
        button_container = QWidget()
        button_container.setStyleSheet("background: #f8fafc; border-top: 1px solid rgba(148, 163, 184, 0.2);")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(24, 14, 24, 14)
        button_layout.addStretch()
        
        save_btn = QPushButton("保存")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #6366f1;
                color: white;
                padding: 10px 36px;
                font-size: 13px;
                font-weight: 600;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: #4f46e5;
            }
        """)
        save_btn.clicked.connect(dialog.accept)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #475569;
                padding: 10px 36px;
                font-size: 13px;
                font-weight: 500;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: #eef2ff;
                color: #6366f1;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        main_layout.addWidget(button_container)
        
        try:
            if dialog.exec_() == QDialog.Accepted:
                self.config_manager.set("hotkey.enabled", hotkey_enabled_checkbox.isChecked())
                self.config_manager.set("hotkey.trigger_key", hotkey_input.text().strip() or DEFAULT_TRIGGER_KEY)
                self.config_manager.set("window.follow_mouse", follow_mouse_checkbox.isChecked())
                self.config_manager.set("window.hide_on_focus_loss", hide_on_focus_loss_checkbox.isChecked())
                self.config_manager.set("search.max_results", max_results_spinbox.value())
                
                self._set_autostart(autostart_checkbox.isChecked())

                # Save appearance settings
                self.config_manager.set("appearance.background_type", bg_type_combo.currentData())
                self.config_manager.set("appearance.background_color", solid_color_btn.property("color_value"))
                self.config_manager.set("appearance.background_image", image_path_input.text())
                self.config_manager.set("appearance.accent_color", accent_color_btn.property("color_value"))
                self.update()  # Repaint main panel with new background
                
                # Save plugin enable/disable state
                new_enabled = []
                for plugin_id, checkbox in plugin_enable_checkboxes.items():
                    if checkbox.isChecked():
                        new_enabled.append(plugin_id)
                        # Enable plugin if not already loaded
                        if plugin_id not in self.plugin_system.plugins:
                            self.plugin_system.load_plugin(plugin_id)
                    else:
                        # Disable plugin if currently loaded
                        if plugin_id in self.plugin_system.plugins:
                            self.plugin_system.unload_plugin(plugin_id)
                self.config_manager.set("plugin.enabled_plugins", new_enabled)
                
                # Save per-plugin config to config/plugins/[plugin_id].json
                for plugin_id, widgets in plugin_settings_widgets.items():
                    settings = {}
                    for setting_key, widget in widgets.items():
                        value = widget.text()
                        settings[setting_key] = value
                    self.plugin_system.set_plugin_config(plugin_id, settings)
                    # Apply settings to loaded plugin instance
                    if plugin_id in self.plugin_system.plugins:
                        self.plugin_system.plugins[plugin_id].apply_settings(settings)
                
                # Reload app grid to reflect plugin enable/disable changes
                self._load_apps()
        finally:
            self._settings_dialog = None
    
    def update_search_results(self, results: list):
        """Update search results list"""
        try:
            self.search_results.clear()
            
            for result in results:
                name = result.get('name', '')
                path = result.get('path', '')
                item = QListWidgetItem(f"  {name}\n  {path}")
                item.setData(Qt.UserRole, result)
                self.search_results.addItem(item)
            
            self.logger.debug(f"Updated search results: {len(results)} items")
            
        except Exception as e:
            self.logger.error(f"Failed to update search results: {e}")
    
    def _on_search_result_clicked(self, item: QListWidgetItem):
        """Handle search result double click"""
        try:
            result = item.data(Qt.UserRole)
            path = result.get("path")
            
            if os.name == 'nt':
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', path])
            
            self.hide()
            self.logger.info(f"Opened file: {path}")
            
        except Exception as e:
            self.logger.error(f"Failed to open file: {e}", exc_info=True)
    
    def focus_search(self):
        """Focus the search box"""
        self.search_box.setFocus()
        self.search_box.selectAll()
    
    def clear_search(self):
        """Clear search box and results"""
        self.search_box.clear()
        self.search_results.clear()
        self.stacked_widget.setCurrentWidget(self.app_grid_widget)
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def _start_mouse_listener(self):
        """Start global mouse listener using pynput"""
        def on_click(x, y, button, pressed):
            if pressed and button == mouse.Button.left:
                if not self.isVisible():
                    return
                
                hide_on_focus_loss = self.config_manager.get("window.hide_on_focus_loss", True)
                if not hide_on_focus_loss:
                    return
                
                local_pos = self.mapFromGlobal(self.cursor().pos())
                in_window = self.rect().contains(local_pos)
                settings_visible = self._settings_dialog and self._settings_dialog.isVisible()
                
                if not in_window and not settings_visible:
                    QTimer.singleShot(0, self._hide_and_clear)
        
        self._mouse_listener = mouse.Listener(on_click=on_click)
        self._mouse_listener.start()
        self.logger.debug("Global mouse listener started")
    
    def _hide_and_clear(self):
        """Hide window and clear search (called from mouse listener thread)"""
        self.hide()
        self.clear_search()

    def _is_autostart_enabled(self) -> bool:
        """Check if autostart is enabled in Windows registry"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "Larj")
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception as e:
            self.logger.error(f"Failed to check autostart: {e}")
            return False

    def _set_autostart(self, enabled: bool):
        """Enable or disable autostart in Windows registry"""
        try:
            import winreg
            import sys
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_WRITE
            )
            
            if enabled:
                exe_path = sys.executable
                if exe_path.endswith("python.exe"):
                    script_path = os.path.abspath("main.py")
                    value = f'"{exe_path}" "{script_path}"'
                else:
                    value = f'"{exe_path}"'
                winreg.SetValueEx(key, "Larj", 0, winreg.REG_SZ, value)
                self.logger.info("Autostart enabled")
            else:
                try:
                    winreg.DeleteValue(key, "Larj")
                    self.logger.info("Autostart disabled")
                except FileNotFoundError:
                    pass
            
            winreg.CloseKey(key)
        except Exception as e:
            self.logger.error(f"Failed to set autostart: {e}")

    def closeEvent(self, event):
        """Handle close event - stop mouse listener"""
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        super().closeEvent(event)

    def paintEvent(self, event):
        """Paint the background using configured appearance settings"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bg_type = self.config_manager.get("appearance.background_type", "solid")
        bg_color = self.config_manager.get("appearance.background_color", "#f8fafc")

        if bg_type == "image":
            image_path = self.config_manager.get("appearance.background_image", "")
            if image_path and os.path.exists(image_path):
                cache_key = (image_path, self.size().width(), self.size().height())
                if self._bg_pixmap_cache is not None and self._bg_pixmap_cache[0] == cache_key:
                    scaled = self._bg_pixmap_cache[1]
                else:
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(
                            self.size(),
                            Qt.KeepAspectRatioByExpanding,
                            Qt.SmoothTransformation,
                        )
                        self._bg_pixmap_cache = (cache_key, scaled)
                    else:
                        scaled = None
                if scaled is not None:
                    painter.drawPixmap(0, 0, scaled)
                    # Subtle border: slate-400 at ~25% opacity
                    painter.setPen(QPen(QColor(148, 163, 184, 64), 1))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 18, 18)
                    super().paintEvent(event)
                    return

        color = QColor(bg_color)
        painter.setBrush(QBrush(color))
        # Subtle border: slate-400 at ~25% opacity
        painter.setPen(QPen(QColor(148, 163, 184, 64), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 18, 18)

        super().paintEvent(event)

    def focusOutEvent(self, event):
        """Hide the panel when focus is lost by clicking outside."""
        hide_on_focus_loss = self.config_manager.get("window.hide_on_focus_loss", True)
        if hide_on_focus_loss and not (self._settings_dialog and self._settings_dialog.isVisible()):
            self.hide()
            self.clear_search()
        super().focusOutEvent(event)

    def _update_memory_usage(self):
        """Update memory usage indicator"""
        try:
            memory_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
            self.memory_label.setText(f"内存: {memory_mb:.1f} MB")
        except Exception:
            self.memory_label.setText(f"内存: {self.MEMORY_PLACEHOLDER}")
