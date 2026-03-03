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
    QMenu, QAction, QInputDialog, QColorDialog, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QMimeData, QPoint
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
    MODERN_STYLE = """
    QWidget#mainPanel {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 #f8fafc,
            stop: 1 #f1f5f9
        );
        border-radius: 16px;
        border: 1px solid #e2e8f0;
    }
    
    QLineEdit#searchBox {
        padding: 14px 20px;
        font-size: 15px;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        background: #ffffff;
        color: #1e293b;
        selection-background-color: #3b82f6;
    }
    
    QLineEdit#searchBox:focus {
        border-color: #3b82f6;
        background: #ffffff;
    }
    
    QLineEdit#searchBox::placeholder {
        color: #94a3b8;
    }
    
    QPushButton#settingsBtn {
        padding: 10px 20px;
        font-size: 13px;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-weight: 500;
        border: none;
        border-radius: 10px;
        background: #f1f5f9;
        color: #475569;
    }
    
    QPushButton#settingsBtn:hover {
        background: #e2e8f0;
        color: #1e293b;
    }
    
    QPushButton#settingsBtn:pressed {
        background: #cbd5e1;
    }
    
    QScrollArea {
        border: none;
        background: transparent;
    }
    
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 4px 0;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical {
        background: #cbd5e1;
        border-radius: 4px;
        min-height: 30px;
    }
    
    QScrollBar::handle:vertical:hover {
        background: #94a3b8;
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
        padding: 12px 16px;
        border-radius: 10px;
        margin: 2px 4px;
        background: transparent;
        color: #334155;
    }
    
    QListWidget::item:hover {
        background: #f1f5f9;
    }
    
    QListWidget::item:selected {
        background: #3b82f6;
        color: #ffffff;
    }
    
    QLabel#memoryLabel {
        color: #94a3b8;
        font-size: 11px;
        font-family: "Segoe UI", sans-serif;
        padding: 4px 8px;
        background: #f8fafc;
        border-radius: 6px;
    }
    """
    
    APP_BUTTON_STYLE = """
    QPushButton {
        font-size: 12px;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-weight: 500;
        border: none;
        border-radius: 12px;
        background: #ffffff;
        color: #334155;
    }
    
    QPushButton:hover {
        background: #f8fafc;
        border: 2px solid #3b82f6;
    }
    
    QPushButton:pressed {
        background: #f1f5f9;
    }
    """
    
    ADD_BUTTON_STYLE = """
    QPushButton {
        padding: 16px;
        font-size: 13px;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-weight: 500;
        border: 2px dashed #cbd5e1;
        border-radius: 12px;
        background: transparent;
        color: #64748b;
    }
    
    QPushButton:hover {
        background: #f8fafc;
        border-color: #3b82f6;
        color: #3b82f6;
    }
    """
    
    DIALOG_STYLE = """
    QDialog {
        background: #ffffff;
        border-radius: 16px;
    }
    
    QLabel {
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-size: 13px;
        color: #334155;
    }
    
    QLineEdit {
        padding: 10px 14px;
        font-size: 13px;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        background: #f8fafc;
        color: #1e293b;
    }
    
    QLineEdit:focus {
        border-color: #3b82f6;
        background: #ffffff;
    }
    
    QCheckBox {
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-size: 13px;
        color: #334155;
        spacing: 8px;
    }
    
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid #cbd5e1;
        background: #ffffff;
    }
    
    QCheckBox::indicator:checked {
        background: #3b82f6;
        border-color: #3b82f6;
    }
    
    QSpinBox {
        padding: 8px 12px;
        font-size: 13px;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        background: #f8fafc;
        color: #1e293b;
    }
    
    QSpinBox:focus {
        border-color: #3b82f6;
    }
    
    QPushButton {
        padding: 10px 20px;
        font-size: 13px;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-weight: 500;
        border: none;
        border-radius: 8px;
    }
    
    QPushButton#detectBtn {
        background: #f1f5f9;
        color: #475569;
    }
    
    QPushButton#detectBtn:hover {
        background: #e2e8f0;
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
        
        self._setup_ui()
        self._connect_signals()
        self._load_apps()
        self._start_mouse_listener()
        
        self.logger.info("MainPanel initialized")
    
    def _setup_ui(self):
        """Setup the user interface"""
        self.setObjectName("mainPanel")
        self.setAutoFillBackground(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("搜索文件或输入命令...")
        self.search_box.setMinimumHeight(48)
        header_layout.addWidget(self.search_box, 1)

        self.settings_button = QPushButton("设置")
        self.settings_button.setObjectName("settingsBtn")
        self.settings_button.setFixedSize(80, 44)
        self.settings_button.clicked.connect(self._on_settings_clicked)
        header_layout.addWidget(self.settings_button)
        layout.addLayout(header_layout)
        
        self.stacked_widget = QStackedWidget()
        
        self.app_grid_widget = QWidget()
        self.app_grid_widget.setStyleSheet("background: transparent;")
        self.app_grid_layout = QVBoxLayout(self.app_grid_widget)
        self.app_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.app_grid_layout.setSpacing(12)
        
        app_scroll = QScrollArea()
        app_scroll.setWidgetResizable(True)
        app_scroll.setFrameShape(QFrame.NoFrame)
        app_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        app_scroll.setStyleSheet("background: transparent;")
        
        app_container = QWidget()
        app_container.setStyleSheet("background: transparent;")
        self.app_grid = QGridLayout(app_container)
        self.app_grid.setSpacing(12)
        self.app_grid.setContentsMargins(4, 4, 4, 4)
        app_scroll.setWidget(app_container)
        
        self.app_grid_layout.addWidget(app_scroll)
        
        self.add_app_button = QPushButton("+ 添加应用")
        self.add_app_button.setStyleSheet(ModernStyle.ADD_BUTTON_STYLE)
        self.add_app_button.setMinimumHeight(52)
        self.add_app_button.setCursor(Qt.PointingHandCursor)
        self.add_app_button.clicked.connect(self._on_add_app_clicked)
        self.app_grid_layout.addWidget(self.add_app_button)
        
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
                padding: 14px 18px;
                border-radius: 10px;
                margin: 3px 4px;
                background: transparent;
                color: #334155;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
            }
            QListWidget::item:hover {
                background: #f1f5f9;
            }
            QListWidget::item:selected {
                background: #3b82f6;
                color: #ffffff;
            }
        """)
        self.search_results.setSpacing(2)
        self.search_results.itemDoubleClicked.connect(self._on_search_result_clicked)
        search_results_layout.addWidget(self.search_results)
        
        self.stacked_widget.addWidget(self.app_grid_widget)
        self.stacked_widget.addWidget(self.search_results_widget)
        
        layout.addWidget(self.stacked_widget)
        
        footer_layout = QHBoxLayout()
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
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 40))
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
    
    def _create_plugin_button(self, plugin_item: dict) -> QPushButton:
        """Create a button for a plugin"""
        plugin = plugin_item.get("plugin_instance")
        metadata = plugin.get_metadata()
        
        button = QPushButton(metadata.get("name", "Plugin"))
        button.setFixedSize(130, 90)
        button.setStyleSheet(ModernStyle.APP_BUTTON_STYLE)
        button.setCursor(Qt.PointingHandCursor)
        
        button.setProperty("plugin_data", plugin_item)
        button.clicked.connect(lambda: self._on_plugin_clicked(plugin))
        
        from PyQt5.QtGui import QFont
        button.setFont(QFont("Segoe UI", 11, QFont.Bold))
        
        return button
    
    def _on_plugin_clicked(self, plugin):
        """Handle plugin button click"""
        try:
            if self.plugin_system:
                self.plugin_system.handle_plugin_click(plugin)
        except Exception as e:
            self.logger.error(f"Failed to handle plugin click: {e}", exc_info=True)
    
    def _create_app_button(self, app: dict) -> QPushButton:
        """Create a button for an app"""
        button = QPushButton(app.get("name", "Unknown"))
        button.setFixedSize(130, 90)
        button.setStyleSheet(ModernStyle.APP_BUTTON_STYLE)
        button.setCursor(Qt.PointingHandCursor)
        
        button.setProperty("app_data", app)
        button.clicked.connect(lambda: self._on_app_clicked(app))
        
        icon = extract_icon_from_file(app.get("path", ""))
        if not icon.isNull():
            button.setIcon(icon)
            button.setIconSize(button.size() * 0.4)
        
        button.setContextMenuPolicy(Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(lambda pos, b=button, a=app: self._show_app_context_menu(pos, b, a))
        
        button.setAcceptDrops(True)
        button.drag_start_pos = None
        
        return button
    
    def _show_app_context_menu(self, pos, button, app):
        """Show context menu for app button"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
                color: #334155;
            }
            QMenu::item:selected {
                background: #f1f5f9;
            }
            QMenu::item:pressed {
                background: #e2e8f0;
            }
        """)
        
        edit_action = menu.addAction("编辑")
        edit_action.triggered.connect(lambda: self._edit_app(app))

        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(lambda: self._rename_app(app))
        
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self._delete_app(app))
        
        menu.addSeparator()
        
        move_up_action = menu.addAction("上移")
        move_up_action.triggered.connect(lambda: self._move_app(app, -1))
        
        move_down_action = menu.addAction("下移")
        move_down_action.triggered.connect(lambda: self._move_app(app, 1))
        
        menu.exec_(button.mapToGlobal(pos))
    
    def _edit_app(self, app: dict):
        """Edit application"""
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑应用")
        dialog.setModal(True)
        dialog.setMinimumWidth(350)
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
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 8px 16px;
                    border-radius: 4px;
                    color: #334155;
                }
                QMenu::item:selected {
                    background: #f1f5f9;
                }
            """)
            
            add_app_action = menu.addAction("添加应用程序")
            add_folder_action = menu.addAction("添加文件夹")
            
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
        dialog.setMinimumSize(500, 500)
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
                padding: 12px 24px;
                margin: 0;
                background: #f8fafc;
                color: #64748b;
                border: none;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #3b82f6;
                border-bottom: 2px solid #3b82f6;
            }
            QTabBar::tab:hover:!selected {
                background: #f1f5f9;
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
                        border-radius: 12px;
                        border: 1px solid #e2e8f0;
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
                name_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #1e293b; background: transparent;")
                header_layout.addWidget(name_label)
                
                version_label = QLabel(f"v{metadata.get('version', '1.0')}")
                version_label.setStyleSheet("font-size: 12px; color: #94a3b8; background: transparent;")
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
                        widget.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px;")
                        
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
        appearance_layout.setSpacing(16)
        appearance_layout.setContentsMargins(24, 24, 24, 24)

        color_buttons = {}

        def _create_color_picker(initial_color: str, parent_dialog: QDialog) -> QPushButton:
            btn = QPushButton()
            btn.setFixedSize(80, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"background: {initial_color}; border: 2px solid #e2e8f0; border-radius: 6px;")
            btn.setProperty("color_value", initial_color)

            def on_click():
                current = QColor(btn.property("color_value") or initial_color)
                chosen = QColorDialog.getColor(current, parent_dialog, "选择颜色", QColorDialog.ShowAlphaChannel)
                if chosen.isValid():
                    hex_color = chosen.name(QColor.HexRgb)
                    btn.setProperty("color_value", hex_color)
                    btn.setStyleSheet(f"background: {hex_color}; border: 2px solid #e2e8f0; border-radius: 6px;")

            btn.clicked.connect(on_click)
            return btn

        # === 预设主题 ===
        preset_group = QWidget()
        preset_group.setStyleSheet("background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;")
        preset_layout = QVBoxLayout(preset_group)
        preset_layout.setSpacing(12)
        preset_layout.setContentsMargins(16, 16, 16, 16)

        preset_title = QLabel("预设主题")
        preset_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #1e293b; background: transparent;")
        preset_layout.addWidget(preset_title)

        preset_btn_layout = QHBoxLayout()
        preset_btn_layout.setSpacing(8)

        presets = [
            ("默认蓝", "#3b82f6", "#f8fafc", "#f1f5f9"),
            ("深邃紫", "#8b5cf6", "#1e1b4b", "#312e81"),
            ("森林绿", "#10b981", "#ecfdf5", "#d1fae5"),
            ("暖阳橙", "#f59e0b", "#fffbeb", "#fef3c7"),
            ("玫瑰红", "#f43f5e", "#fff1f2", "#ffe4e6"),
            ("暗夜黑", "#64748b", "#0f172a", "#1e293b"),
        ]

        def apply_preset(name, accent, start, end):
            if "accent_btn" in color_buttons:
                color_buttons["accent_btn"].setProperty("color_value", accent)
                color_buttons["accent_btn"].setStyleSheet(f"background: {accent}; border: 2px solid #e2e8f0; border-radius: 6px;")
            if "grad_start_btn" in color_buttons:
                color_buttons["grad_start_btn"].setProperty("color_value", start)
                color_buttons["grad_start_btn"].setStyleSheet(f"background: {start}; border: 2px solid #e2e8f0; border-radius: 6px;")
            if "grad_end_btn" in color_buttons:
                color_buttons["grad_end_btn"].setProperty("color_value", end)
                color_buttons["grad_end_btn"].setStyleSheet(f"background: {end}; border: 2px solid #e2e8f0; border-radius: 6px;")

        for preset_name, accent, start, end in presets:
            btn = QPushButton(preset_name)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 {start}, stop:1 {end});
                    color: {accent};
                    border: 2px solid {accent};
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 500;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background: {accent};
                    color: white;
                }}
            """)
            btn.clicked.connect(lambda checked, n=preset_name, a=accent, s=start, e=end: apply_preset(n, a, s, e))
            preset_btn_layout.addWidget(btn)

        preset_layout.addLayout(preset_btn_layout)
        appearance_layout.addWidget(preset_group)

        # === 背景设置 ===
        bg_group = QWidget()
        bg_group.setStyleSheet("background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;")
        bg_group_layout = QVBoxLayout(bg_group)
        bg_group_layout.setSpacing(16)
        bg_group_layout.setContentsMargins(16, 16, 16, 16)

        bg_title = QLabel("背景设置")
        bg_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #1e293b; background: transparent;")
        bg_group_layout.addWidget(bg_title)

        bg_type_layout = QHBoxLayout()
        bg_type_layout.setSpacing(12)
        bg_type_label = QLabel("背景类型")
        bg_type_label.setStyleSheet("font-size: 13px; color: #475569; background: transparent; min-width: 70px;")
        bg_type_layout.addWidget(bg_type_label)

        bg_type_combo = QComboBox()
        bg_type_combo.addItem("渐变色", "gradient")
        bg_type_combo.addItem("纯色", "solid")
        bg_type_combo.addItem("图片", "image")
        current_bg_type = self.config_manager.get("appearance.background_type", "gradient")
        for idx in range(bg_type_combo.count()):
            if bg_type_combo.itemData(idx) == current_bg_type:
                bg_type_combo.setCurrentIndex(idx)
                break
        bg_type_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px; font-size: 13px; border: 2px solid #e2e8f0;
                border-radius: 8px; background: #ffffff; color: #1e293b; min-width: 120px;
            }
            QComboBox:hover { border-color: #3b82f6; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #64748b; margin-right: 8px; }
        """)
        bg_type_layout.addWidget(bg_type_combo)
        bg_type_layout.addStretch()
        bg_group_layout.addLayout(bg_type_layout)

        gradient_widget = QWidget()
        gradient_widget.setStyleSheet("background: transparent;")
        gradient_layout = QVBoxLayout(gradient_widget)
        gradient_layout.setSpacing(12)
        gradient_layout.setContentsMargins(0, 0, 0, 0)

        grad_start_color = self.config_manager.get("appearance.background_gradient_start", "#f8fafc")
        grad_end_color = self.config_manager.get("appearance.background_gradient_end", "#f1f5f9")

        grad_start_row = QHBoxLayout()
        grad_start_row.setSpacing(12)
        grad_start_label = QLabel("渐变起始色")
        grad_start_label.setStyleSheet("font-size: 13px; color: #475569; background: transparent; min-width: 70px;")
        grad_start_row.addWidget(grad_start_label)
        grad_start_btn = _create_color_picker(grad_start_color, dialog)
        color_buttons["grad_start_btn"] = grad_start_btn
        grad_start_row.addWidget(grad_start_btn)

        grad_start_hex = QLabel(grad_start_color)
        grad_start_hex.setStyleSheet("font-size: 12px; color: #94a3b8; background: transparent; font-family: monospace;")
        grad_start_btn.clicked.connect(lambda: grad_start_hex.setText(grad_start_btn.property("color_value") or grad_start_color))
        grad_start_row.addWidget(grad_start_hex)
        grad_start_row.addStretch()
        gradient_layout.addLayout(grad_start_row)

        grad_end_row = QHBoxLayout()
        grad_end_row.setSpacing(12)
        grad_end_label = QLabel("渐变结束色")
        grad_end_label.setStyleSheet("font-size: 13px; color: #475569; background: transparent; min-width: 70px;")
        grad_end_row.addWidget(grad_end_label)
        grad_end_btn = _create_color_picker(grad_end_color, dialog)
        color_buttons["grad_end_btn"] = grad_end_btn
        grad_end_row.addWidget(grad_end_btn)

        grad_end_hex = QLabel(grad_end_color)
        grad_end_hex.setStyleSheet("font-size: 12px; color: #94a3b8; background: transparent; font-family: monospace;")
        grad_end_btn.clicked.connect(lambda: grad_end_hex.setText(grad_end_btn.property("color_value") or grad_end_color))
        grad_end_row.addWidget(grad_end_hex)
        grad_end_row.addStretch()
        gradient_layout.addLayout(grad_end_row)

        grad_dir_row = QHBoxLayout()
        grad_dir_row.setSpacing(12)
        grad_dir_label = QLabel("渐变方向")
        grad_dir_label.setStyleSheet("font-size: 13px; color: #475569; background: transparent; min-width: 70px;")
        grad_dir_row.addWidget(grad_dir_label)
        grad_dir_combo = QComboBox()
        grad_dir_combo.addItem("从上到下", "vertical")
        grad_dir_combo.addItem("从左到右", "horizontal")
        grad_dir_combo.addItem("对角线", "diagonal")
        grad_dir_combo.addItem("径向渐变", "radial")
        current_dir = self.config_manager.get("appearance.gradient_direction", "vertical")
        for idx in range(grad_dir_combo.count()):
            if grad_dir_combo.itemData(idx) == current_dir:
                grad_dir_combo.setCurrentIndex(idx)
                break
        grad_dir_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px; font-size: 13px; border: 2px solid #e2e8f0;
                border-radius: 8px; background: #ffffff; color: #1e293b; min-width: 120px;
            }
            QComboBox:hover { border-color: #3b82f6; }
            QComboBox::drop-down { border: none; }
        """)
        grad_dir_row.addWidget(grad_dir_combo)
        grad_dir_row.addStretch()
        gradient_layout.addLayout(grad_dir_row)

        bg_group_layout.addWidget(gradient_widget)

        solid_widget = QWidget()
        solid_widget.setStyleSheet("background: transparent;")
        solid_layout = QHBoxLayout(solid_widget)
        solid_layout.setSpacing(12)
        solid_layout.setContentsMargins(0, 0, 0, 0)
        solid_label = QLabel("背景颜色")
        solid_label.setStyleSheet("font-size: 13px; color: #475569; background: transparent; min-width: 70px;")
        solid_layout.addWidget(solid_label)
        solid_color = self.config_manager.get("appearance.background_color", "#f8fafc")
        solid_color_btn = _create_color_picker(solid_color, dialog)
        color_buttons["solid_color_btn"] = solid_color_btn
        solid_layout.addWidget(solid_color_btn)
        solid_layout.addStretch()
        bg_group_layout.addWidget(solid_widget)

        image_widget = QWidget()
        image_widget.setStyleSheet("background: transparent;")
        image_layout = QHBoxLayout(image_widget)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(12)
        image_label = QLabel("背景图片")
        image_label.setStyleSheet("font-size: 13px; color: #475569; background: transparent; min-width: 70px;")
        image_layout.addWidget(image_label)
        image_path_input = QLineEdit()
        image_path_input.setText(self.config_manager.get("appearance.background_image", ""))
        image_path_input.setReadOnly(True)
        image_path_input.setPlaceholderText("选择图片文件...")
        image_path_input.setStyleSheet("padding: 8px 12px; font-size: 13px; border: 2px solid #e2e8f0; border-radius: 8px; background: #ffffff;")
        image_layout.addWidget(image_path_input, 1)
        browse_btn = QPushButton("浏览")
        browse_btn.setFixedSize(70, 36)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(
            "QPushButton { background: #3b82f6; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: #2563eb; }"
        )

        def pick_image():
            path, _ = QFileDialog.getOpenFileName(
                dialog, "选择背景图片", "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)"
            )
            if path:
                image_path_input.setText(path)

        browse_btn.clicked.connect(pick_image)
        image_layout.addWidget(browse_btn)
        bg_group_layout.addWidget(image_widget)

        def _update_appearance_sections(index=None):
            selected = bg_type_combo.currentData()
            gradient_widget.setVisible(selected == "gradient")
            solid_widget.setVisible(selected == "solid")
            image_widget.setVisible(selected == "image")

        bg_type_combo.currentIndexChanged.connect(_update_appearance_sections)
        _update_appearance_sections()

        appearance_layout.addWidget(bg_group)

        # === 窗口样式 ===
        style_group = QWidget()
        style_group.setStyleSheet("background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;")
        style_group_layout = QVBoxLayout(style_group)
        style_group_layout.setSpacing(16)
        style_group_layout.setContentsMargins(16, 16, 16, 16)

        style_title = QLabel("窗口样式")
        style_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #1e293b; background: transparent;")
        style_group_layout.addWidget(style_title)

        corner_row = QHBoxLayout()
        corner_row.setSpacing(12)
        corner_label = QLabel("圆角大小")
        corner_label.setStyleSheet("font-size: 13px; color: #475569; background: transparent; min-width: 70px;")
        corner_row.addWidget(corner_label)
        corner_spinbox = QSpinBox()
        corner_spinbox.setRange(0, 32)
        corner_spinbox.setValue(self.config_manager.get("appearance.border_radius", 16))
        corner_spinbox.setStyleSheet("padding: 6px 10px; font-size: 13px; border: 2px solid #e2e8f0; border-radius: 8px; background: #ffffff;")
        corner_row.addWidget(corner_spinbox)
        corner_row.addStretch()
        style_group_layout.addLayout(corner_row)

        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(12)
        opacity_label = QLabel("窗口透明度")
        opacity_label.setStyleSheet("font-size: 13px; color: #475569; background: transparent; min-width: 70px;")
        opacity_row.addWidget(opacity_label)
        opacity_spinbox = QSpinBox()
        opacity_spinbox.setRange(50, 100)
        opacity_spinbox.setValue(int(self.config_manager.get("window.opacity", 95)))
        opacity_spinbox.setSuffix("%")
        opacity_spinbox.setStyleSheet("padding: 6px 10px; font-size: 13px; border: 2px solid #e2e8f0; border-radius: 8px; background: #ffffff;")
        opacity_row.addWidget(opacity_spinbox)
        opacity_row.addStretch()
        style_group_layout.addLayout(opacity_row)

        accent_row = QHBoxLayout()
        accent_row.setSpacing(12)
        accent_label = QLabel("主题强调色")
        accent_label.setStyleSheet("font-size: 13px; color: #475569; background: transparent; min-width: 70px;")
        accent_row.addWidget(accent_label)
        accent_color = self.config_manager.get("appearance.accent_color", "#3b82f6")
        accent_color_btn = _create_color_picker(accent_color, dialog)
        color_buttons["accent_btn"] = accent_color_btn
        accent_row.addWidget(accent_color_btn)

        accent_hex = QLabel(accent_color)
        accent_hex.setStyleSheet("font-size: 12px; color: #94a3b8; background: transparent; font-family: monospace;")
        accent_color_btn.clicked.connect(lambda: accent_hex.setText(accent_color_btn.property("color_value") or accent_color))
        accent_row.addWidget(accent_hex)
        accent_row.addStretch()
        style_group_layout.addLayout(accent_row)

        shadow_row = QHBoxLayout()
        shadow_row.setSpacing(12)
        shadow_label = QLabel("阴影效果")
        shadow_label.setStyleSheet("font-size: 13px; color: #475569; background: transparent; min-width: 70px;")
        shadow_row.addWidget(shadow_label)
        shadow_checkbox = QCheckBox()
        shadow_checkbox.setChecked(self.config_manager.get("appearance.enable_shadow", True))
        shadow_checkbox.setStyleSheet("background: transparent;")
        shadow_row.addWidget(shadow_checkbox)
        shadow_row.addStretch()
        style_group_layout.addLayout(shadow_row)

        appearance_layout.addWidget(style_group)
        appearance_layout.addStretch()
        tab_widget.addTab(appearance_widget, "外观")
        # ── end Appearance tab ───────────────────────────────────────────────

        main_layout.addWidget(tab_widget)
        
        button_container = QWidget()
        button_container.setStyleSheet("background: #f8fafc; border-top: 1px solid #e2e8f0;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(24, 16, 24, 16)
        button_layout.addStretch()
        
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                padding: 10px 32px;
                font-size: 13px;
                font-weight: 500;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #2563eb;
            }
        """)
        save_btn.clicked.connect(dialog.accept)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #475569;
                padding: 10px 32px;
                font-size: 13px;
                font-weight: 500;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #e2e8f0;
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

                # Save appearance settings
                self.config_manager.set("appearance.background_type", bg_type_combo.currentData())
                self.config_manager.set("appearance.background_gradient_start", grad_start_btn.property("color_value"))
                self.config_manager.set("appearance.background_gradient_end", grad_end_btn.property("color_value"))
                self.config_manager.set("appearance.background_color", solid_color_btn.property("color_value"))
                self.config_manager.set("appearance.background_image", image_path_input.text())
                self.config_manager.set("appearance.accent_color", accent_color_btn.property("color_value"))
                self.config_manager.set("appearance.gradient_direction", grad_dir_combo.currentData())
                self.config_manager.set("appearance.border_radius", corner_spinbox.value())
                self.config_manager.set("window.opacity", opacity_spinbox.value() / 100.0)
                self.config_manager.set("appearance.enable_shadow", shadow_checkbox.isChecked())
                self.update()
                
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

        border_radius = self.config_manager.get("appearance.border_radius", 16)
        enable_shadow = self.config_manager.get("appearance.enable_shadow", True)
        bg_type = self.config_manager.get("appearance.background_type", "gradient")

        if enable_shadow:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 15))
            painter.drawRoundedRect(3, 3, self.width() - 6, self.height() - 6, border_radius, border_radius)

        if bg_type == "solid":
            color = QColor(self.config_manager.get("appearance.background_color", "#f8fafc"))
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor("#e2e8f0"), 1))
            painter.drawRoundedRect(self.rect(), border_radius, border_radius)
        elif bg_type == "image":
            image_path = self.config_manager.get("appearance.background_image", "")
            painted = False
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        self.size(),
                        Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation,
                    )
                    painter.drawRoundedRect(self.rect(), border_radius, border_radius)
                    painter.setClipRect(self.rect())
                    painter.drawPixmap(0, 0, scaled)
                    painter.setPen(QPen(QColor("#e2e8f0"), 1))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRoundedRect(self.rect(), border_radius, border_radius)
                    painted = True
            if not painted:
                self._paint_gradient(painter, border_radius)
        else:
            self._paint_gradient(painter, border_radius)

        super().paintEvent(event)

    def _paint_gradient(self, painter, border_radius=16):
        """Paint a gradient background with configurable direction."""
        start = self.config_manager.get("appearance.background_gradient_start", "#f8fafc")
        end = self.config_manager.get("appearance.background_gradient_end", "#f1f5f9")
        direction = self.config_manager.get("appearance.gradient_direction", "vertical")

        if direction == "vertical":
            gradient = QLinearGradient(0, 0, 0, self.height())
        elif direction == "horizontal":
            gradient = QLinearGradient(0, 0, self.width(), 0)
        elif direction == "diagonal":
            gradient = QLinearGradient(0, 0, self.width(), self.height())
        else:
            gradient = QLinearGradient(0, 0, 0, self.height())

        gradient.setColorAt(0, QColor(start))
        gradient.setColorAt(1, QColor(end))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#e2e8f0"), 1))
        painter.drawRoundedRect(self.rect(), border_radius, border_radius)

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
