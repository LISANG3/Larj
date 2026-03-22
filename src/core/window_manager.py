#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Window Manager - Manages the floating panel window
Handles window display, positioning, animations, and interactions
"""

import logging
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QCursor

from src.ui.main_panel import MainPanel


class WindowManager:
    """
    Window manager - controls the main floating panel window
    """
    
    def __init__(self, config_manager, search_engine, application_manager, plugin_system):
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.search_engine = search_engine
        self.application_manager = application_manager
        self.plugin_system = plugin_system
        
        # Window instance
        self.window = None
        
        # Window properties
        self.width = 600
        self.height = 400
        self.opacity = 1.0
        self.corner_radius = 10
        self.follow_mouse = True
        self.animation_duration = 200
        
        # Load configuration
        self.reload_config()
        
        # Create window
        self._create_window()
        
        self.logger.info("WindowManager initialized")
    
    def reload_config(self):
        """Reload window configuration"""
        try:
            self.width = self.config_manager.get("window.width", 600)
            self.height = self.config_manager.get("window.height", 400)
            configured_opacity = self.config_manager.get("window.opacity", 100)
            self.opacity = max(0.0, min(1.0, float(configured_opacity) / 100.0))
            self.corner_radius = self.config_manager.get("window.corner_radius", 10)
            self.follow_mouse = self.config_manager.get("window.follow_mouse", True)
            self.animation_duration = self.config_manager.get("window.animation_duration", 200)
            
            # Apply to existing window if it exists
            if self.window:
                self.window.setFixedSize(self.width, self.height)
                self.window.setWindowOpacity(self.opacity)
            
            self.logger.info("Window config reloaded")
            
        except Exception as e:
            self.logger.error(f"Failed to reload window config: {e}")
    
    def _create_window(self):
        """Create the main panel window"""
        try:
            self.window = MainPanel(
                self.config_manager,
                self.search_engine,
                self.application_manager,
                self.plugin_system
            )
            
            self.window.setFixedSize(self.width, self.height)
            self.window.setWindowOpacity(self.opacity)
            
            # 设置无边框窗口标志，保持窗口始终置顶
            self.window.setWindowFlags(
                Qt.Window |
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.Tool
            )
            
            # 保持顶层窗口走不透明渲染链路，圆角由 mask 控制。
            self.window.setAttribute(Qt.WA_TranslucentBackground, False)
            self.window.setAttribute(Qt.WA_ShowWithoutActivating, False)
            self.window.refresh_window_shape()
            
            self.logger.info("Main panel window created")
            
        except Exception as e:
            self.logger.error(f"Failed to create window: {e}", exc_info=True)
            raise
    
    def show_window(self):
        """Show the window with animation"""
        try:
            if self.window.isVisible():
                return

            self.window.reset_panel_state()
            
            # Position window
            self._position_window()
            
            # Show window
            self.window.show()
            self.window.update()
            self.window.repaint()
            self.window.activateWindow()
            self.window.raise_()
            self.window.ensure_fresh_show_state()
            
            # Focus search box
            self.window.focus_search()
            
            self.logger.debug("Window shown")
            
        except Exception as e:
            self.logger.error(f"Failed to show window: {e}", exc_info=True)
    
    def hide_window(self):
        """Hide the window with animation"""
        try:
            if not self.window.isVisible():
                return
            
            self.window.hide()
            
            # Clear search
            self.window.reset_panel_state()
            
            self.logger.debug("Window hidden")
            
        except Exception as e:
            self.logger.error(f"Failed to hide window: {e}")
    
    def _position_window(self):
        """Calculate and set window position"""
        try:
            if self.follow_mouse:
                # Get mouse cursor position
                cursor_pos = QCursor.pos()
                
                # Get screen geometry
                screen = QApplication.screenAt(cursor_pos)
                if screen is None:
                    screen = QApplication.primaryScreen()
                
                screen_geometry = screen.availableGeometry()
                
                # Calculate position (right side of cursor by default)
                x = cursor_pos.x() + 20
                y = cursor_pos.y() - self.height // 2
                
                # Adjust if window goes off screen
                if x + self.width > screen_geometry.right():
                    x = cursor_pos.x() - self.width - 20
                
                if y < screen_geometry.top():
                    y = screen_geometry.top() + 10
                elif y + self.height > screen_geometry.bottom():
                    y = screen_geometry.bottom() - self.height - 10
                
                # Set position
                self.window.move(x, y)
            else:
                # Center on screen
                screen = QApplication.primaryScreen()
                screen_geometry = screen.availableGeometry()
                
                x = (screen_geometry.width() - self.width) // 2
                y = (screen_geometry.height() - self.height) // 2
                
                self.window.move(x, y)
            
        except Exception as e:
            self.logger.error(f"Failed to position window: {e}")
    
    def is_visible(self) -> bool:
        """Check if window is visible"""
        return self.window.isVisible() if self.window else False
    
    def close(self):
        """Close the window"""
        if self.window:
            self.window.close()
            self.logger.info("Window closed")
    
    def update_search_results(self, results: list):
        """Update search results in window"""
        if self.window:
            self.window.update_search_results(results)
