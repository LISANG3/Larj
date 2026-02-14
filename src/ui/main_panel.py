#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Panel - The main UI window
Contains search box, app grid, and search results
"""

import logging
import os
from pathlib import Path
import psutil
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QScrollArea, QLabel, QGridLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QFrame, QDialog, QDialogButtonBox, QFormLayout,
    QCheckBox, QSpinBox, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QPixmap
from src.core.hotkey_listener import detect_hotkey, DEFAULT_TRIGGER_KEY


class MainPanel(QWidget):
    """
    Main panel window - the floating panel UI
    """
    
    # Signals
    app_clicked = pyqtSignal(dict)  # app_info
    search_changed = pyqtSignal(str)  # keyword
    
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
        
        self.logger.info("MainPanel initialized")
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Search box and settings at top
        header_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索文件...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border: 2px solid #ddd;
                border-radius: 5px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
            }
        """)
        header_layout.addWidget(self.search_box)

        self.settings_button = QPushButton("设置")
        self.settings_button.setFixedHeight(36)
        self.settings_button.clicked.connect(self._on_settings_clicked)
        header_layout.addWidget(self.settings_button)
        layout.addLayout(header_layout)
        
        # Stacked widget for switching between app grid and search results
        self.stacked_widget = QStackedWidget()
        
        # App grid page
        self.app_grid_widget = QWidget()
        self.app_grid_layout = QVBoxLayout(self.app_grid_widget)
        self.app_grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area for apps
        app_scroll = QScrollArea()
        app_scroll.setWidgetResizable(True)
        app_scroll.setFrameShape(QFrame.NoFrame)
        app_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Container for app grid
        app_container = QWidget()
        self.app_grid = QGridLayout(app_container)
        self.app_grid.setSpacing(10)
        app_scroll.setWidget(app_container)
        
        self.app_grid_layout.addWidget(app_scroll)
        
        # Add button at the end
        self.add_app_button = QPushButton("+ 添加应用")
        self.add_app_button.setStyleSheet("""
            QPushButton {
                padding: 10px;
                font-size: 12px;
                border: 2px dashed #ddd;
                border-radius: 5px;
                background: #f9f9f9;
            }
            QPushButton:hover {
                background: #e9e9e9;
                border-color: #4CAF50;
            }
        """)
        self.add_app_button.clicked.connect(self._on_add_app_clicked)
        self.app_grid_layout.addWidget(self.add_app_button)
        
        # Search results page
        self.search_results_widget = QWidget()
        search_results_layout = QVBoxLayout(self.search_results_widget)
        search_results_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_results = QListWidget()
        self.search_results.setStyleSheet("""
            QListWidget {
                border: none;
                background: transparent;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background: #f0f0f0;
            }
            QListWidget::item:selected {
                background: #4CAF50;
                color: white;
            }
        """)
        self.search_results.itemDoubleClicked.connect(self._on_search_result_clicked)
        search_results_layout.addWidget(self.search_results)
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.app_grid_widget)
        self.stacked_widget.addWidget(self.search_results_widget)
        
        layout.addWidget(self.stacked_widget)
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        self.memory_label = QLabel("内存: -- MB")
        self.memory_label.setStyleSheet("color: #888; font-size: 11px; padding-right: 2px;")
        footer_layout.addWidget(self.memory_label)
        layout.addLayout(footer_layout)

        self._memory_timer = QTimer(self)
        self._memory_timer.timeout.connect(self._update_memory_usage)
        self._memory_timer.start(2000)
        self._update_memory_usage()
        
        # Set window style
        self.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-radius: 10px;
            }
        """)
    
    def _connect_signals(self):
        """Connect UI signals"""
        # Search box text changed
        self.search_box.textChanged.connect(self._on_search_changed)
        
        # Connect to search engine
        self.search_engine.search_completed.connect(self.update_search_results)
    
    def _on_search_changed(self, text: str):
        """Handle search box text change"""
        if text.strip():
            # Switch to search results view
            self.stacked_widget.setCurrentWidget(self.search_results_widget)
            
            # Trigger search
            self.search_engine.search(text)
        else:
            # Switch back to app grid
            self.stacked_widget.setCurrentWidget(self.app_grid_widget)
    
    def _load_apps(self):
        """Load applications into grid"""
        try:
            # Clear existing apps
            for i in reversed(range(self.app_grid.count())):
                self.app_grid.itemAt(i).widget().setParent(None)
            
            # Get apps
            apps = self.application_manager.get_apps()
            
            # Add apps to grid (4 columns)
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
        button.setFixedSize(120, 80)
        button.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background: white;
            }
            QPushButton:hover {
                background: #f0f0f0;
                border-color: #4CAF50;
            }
        """)
        
        # Store app data
        button.setProperty("app_data", app)
        
        # Connect click
        button.clicked.connect(lambda: self._on_app_clicked(app))
        
        return button
    
    def _on_app_clicked(self, app: dict):
        """Handle app button click"""
        try:
            self.application_manager.launch_app(app)
            # Hide window after launch
            self.hide()
        except Exception as e:
            self.logger.error(f"Failed to launch app: {e}", exc_info=True)
    
    def _on_add_app_clicked(self):
        """Handle add app button click"""
        try:
            file_filter = "Applications (*.exe *.bat *.cmd *.lnk);;All Files (*)" if os.name == "nt" else "All Files (*)"
            file_path, _ = QFileDialog.getOpenFileName(self, "选择应用程序", "", file_filter)
            if not file_path:
                return

            app_name = Path(file_path).stem
            self.application_manager.add_app(app_name, file_path)
            self._load_apps()
            self.logger.info(f"Added app: {app_name}")
        except Exception as e:
            self.logger.error(f"Failed to add app: {e}", exc_info=True)
            QMessageBox.warning(self, "添加应用失败", str(e))

    def _on_settings_clicked(self):
        """Open settings dialog"""
        dialog = QDialog(self)
        self._settings_dialog = dialog
        dialog.setWindowTitle("设置")
        dialog.setModal(True)

        form_layout = QFormLayout(dialog)

        hotkey_enabled_checkbox = QCheckBox()
        hotkey_enabled_checkbox.setChecked(self.config_manager.get("hotkey.enabled", True))
        form_layout.addRow("启用热键", hotkey_enabled_checkbox)

        hotkey_widget = QWidget()
        hotkey_layout = QHBoxLayout(hotkey_widget)
        hotkey_layout.setContentsMargins(0, 0, 0, 0)
        hotkey_input = QLineEdit()
        hotkey_input.setText(self.config_manager.get("hotkey.trigger_key", DEFAULT_TRIGGER_KEY))
        detect_hotkey_button = QPushButton("检测")
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

        max_results_spinbox = QSpinBox()
        max_results_spinbox.setRange(10, 500)
        max_results_spinbox.setValue(self.config_manager.get("search.max_results", 50))
        form_layout.addRow("搜索结果上限", max_results_spinbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form_layout.addRow(buttons)

        try:
            if dialog.exec_() == QDialog.Accepted:
                self.config_manager.set("hotkey.enabled", hotkey_enabled_checkbox.isChecked())
                self.config_manager.set("hotkey.trigger_key", hotkey_input.text().strip() or DEFAULT_TRIGGER_KEY)
                self.config_manager.set("window.follow_mouse", follow_mouse_checkbox.isChecked())
                self.config_manager.set("search.max_results", max_results_spinbox.value())
        finally:
            self._settings_dialog = None
    
    def update_search_results(self, results: list):
        """Update search results list"""
        try:
            self.search_results.clear()
            
            for result in results:
                item = QListWidgetItem(f"{result.get('name')} - {result.get('path')}")
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
            
            # Open file with default application
            if os.name == 'nt':  # Windows
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', path])
            
            # Hide window
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
            # Hide window on Escape
            self.hide()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):
        """Hide the panel when focus is lost by clicking outside."""
        if not (self._settings_dialog and self._settings_dialog.isVisible()):
            self.hide()
            self.clear_search()
        super().focusOutEvent(event)

    def _update_memory_usage(self):
        """Update memory usage indicator"""
        try:
            memory_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
            self.memory_label.setText(f"内存: {memory_mb:.1f} MB")
        except Exception:
            self.memory_label.setText("内存: -- MB")
