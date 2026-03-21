#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Larj - Windows Desktop Efficiency Tool
Main entry point
"""

import sys
import os
import logging
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import QSize
from src.core.main_controller import MainController


def create_default_icon():
    """Create a default icon if no icon file exists"""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(59, 130, 246))
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(255, 255, 255))
    painter.setPen(QColor(255, 255, 255))
    font = painter.font()
    font.setPointSize(32)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), 0x0084, "L")
    painter.end()
    
    return QIcon(pixmap)


def setup_logging():
    """Setup logging configuration"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "larj.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main entry point"""
    # Ensure working directory is the application directory
    # This is critical for autostart where CWD might be System32
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Larj application...")
    
    try:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        controller = MainController()
        controller.initialize()
        
        tray_icon = QSystemTrayIcon()
        icon = create_default_icon()
        tray_icon.setIcon(icon)
        tray_icon.setToolTip("Larj - 桌面效率工具")
        
        tray_menu = QMenu()
        
        show_action = QAction("显示/隐藏", app)
        show_action.triggered.connect(lambda: (
            controller.window_manager.hide_window()
            if controller.window_manager.is_visible()
            else controller.window_manager.show_window()
        ))
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("退出", app)
        quit_action.triggered.connect(lambda: (
            controller.shutdown(),
            tray_icon.hide(),
            app.quit()
        ))
        tray_menu.addAction(quit_action)
        
        tray_icon.setContextMenu(tray_menu)
        
        tray_icon.activated.connect(lambda reason: (
            controller.window_manager.show_window()
            if reason == QSystemTrayIcon.DoubleClick
            and not controller.window_manager.is_visible()
            else controller.window_manager.hide_window()
            if reason == QSystemTrayIcon.DoubleClick
            else None
        ))
        
        tray_icon.show()
        
        logger.info("Larj application started successfully")
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
