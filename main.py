#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Larj - Windows Desktop Efficiency Tool
Main entry point
"""

import sys
import logging
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from src.core.main_controller import MainController


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
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Larj application...")
    
    try:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # Keep running in system tray
        
        # Initialize main controller
        controller = MainController()
        controller.initialize()
        
        logger.info("Larj application started successfully")
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
