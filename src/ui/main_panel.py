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
    QMenu, QAction, QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QMimeData, QPoint, QEvent
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPalette, QLinearGradient, QBrush, QPainter, QDrag
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
        
        self._setup_ui()
        self._connect_signals()
        self._load_apps()
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
        
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
        """Load applications into grid"""
        try:
            for i in reversed(range(self.app_grid.count())):
                item = self.app_grid.itemAt(i)
                if item and item.widget():
                    item.widget().setParent(None)
            
            apps = self.application_manager.get_apps()
            
            cols = 4
            for i, app in enumerate(apps):
                row = i // cols
                col = i % cols
                
                app_button = self._create_app_button(app)
                self.app_grid.addWidget(app_button, row, col)
            
            self.logger.debug(f"Loaded {len(apps)} apps")
            
        except Exception as e:
            self.logger.error(f"Failed to load apps: {e}", exc_info=True)
    
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
        """Open settings dialog"""
        dialog = QDialog(self)
        self._settings_dialog = dialog
        dialog.setWindowTitle("设置")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet(ModernStyle.DIALOG_STYLE)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("应用设置")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: 600;
            color: #1e293b;
            padding-bottom: 8px;
        """)
        layout.addWidget(title)

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
        detect_hotkey_button.setObjectName("detectBtn")
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

        layout.addWidget(form_widget)
        layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.setStyleSheet("""
            QPushButton {
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 500;
                border-radius: 8px;
            }
            QPushButton[text="保存"] {
                background: #3b82f6;
                color: white;
            }
            QPushButton[text="保存"]:hover {
                background: #2563eb;
            }
            QPushButton[text="取消"] {
                background: #f1f5f9;
                color: #475569;
            }
            QPushButton[text="取消"]:hover {
                background: #e2e8f0;
            }
        """)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        try:
            if dialog.exec_() == QDialog.Accepted:
                self.config_manager.set("hotkey.enabled", hotkey_enabled_checkbox.isChecked())
                self.config_manager.set("hotkey.trigger_key", hotkey_input.text().strip() or DEFAULT_TRIGGER_KEY)
                self.config_manager.set("window.follow_mouse", follow_mouse_checkbox.isChecked())
                self.config_manager.set("window.hide_on_focus_loss", hide_on_focus_loss_checkbox.isChecked())
                self.config_manager.set("search.max_results", max_results_spinbox.value())
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

    def eventFilter(self, obj, event):
        if (
            self.isVisible()
            and event.type() == QEvent.MouseButtonPress
            and event.button() == Qt.LeftButton
        ):
            hide_on_focus_loss = self.config_manager.get("window.hide_on_focus_loss", True)
            if (
                hide_on_focus_loss
                and not self.geometry().contains(event.globalPos())
                and not (self._settings_dialog and self._settings_dialog.isVisible())
            ):
                self.hide()
                self.clear_search()
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)
        super().closeEvent(event)

    def paintEvent(self, event):
        """Paint the gradient background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#f8fafc"))
        gradient.setColorAt(1, QColor("#f1f5f9"))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)
        
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
