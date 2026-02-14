#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Controller - System coordinator and event bus
Handles module lifecycle, event routing, and dependency management
"""

import logging
from PyQt5.QtCore import QObject, pyqtSignal

from src.core.config_manager import ConfigManager
from src.core.hotkey_listener import HotkeyListener
from src.core.window_manager import WindowManager
from src.core.search_engine import SearchEngine
from src.core.application_manager import ApplicationManager
from src.core.plugin_system import PluginSystem


class MainController(QObject):
    """
    Main controller - coordinates all modules and manages event flow
    Singleton pattern ensures single point of coordination
    """
    
    # Event signals
    show_window_signal = pyqtSignal()
    hide_window_signal = pyqtSignal()
    search_request_signal = pyqtSignal(str)  # keyword
    search_result_signal = pyqtSignal(list)  # results
    launch_app_signal = pyqtSignal(dict)  # app_info
    config_change_signal = pyqtSignal(dict)  # config_data
    config_updated_signal = pyqtSignal()
    plugin_enable_signal = pyqtSignal(str)  # plugin_name
    plugin_disable_signal = pyqtSignal(str)  # plugin_name
    plugin_click_signal = pyqtSignal(object)  # plugin_instance
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        
        # Initialize modules
        self.config_manager = None
        self.hotkey_listener = None
        self.window_manager = None
        self.search_engine = None
        self.application_manager = None
        self.plugin_system = None
        
    def initialize(self):
        """Initialize all modules in correct dependency order"""
        if self._initialized:
            self.logger.warning("Controller already initialized")
            return
            
        try:
            self.logger.info("Initializing MainController...")
            
            # Step 1: Initialize configuration manager first (no dependencies)
            self.logger.info("Initializing ConfigManager...")
            self.config_manager = ConfigManager()
            
            # Step 2: Initialize core modules
            self.logger.info("Initializing ApplicationManager...")
            self.application_manager = ApplicationManager(self.config_manager)
            
            self.logger.info("Initializing SearchEngine...")
            self.search_engine = SearchEngine(self.config_manager)
            
            self.logger.info("Initializing PluginSystem...")
            self.plugin_system = PluginSystem(self.config_manager)
            
            # Step 3: Initialize UI and input modules (depend on core modules)
            self.logger.info("Initializing WindowManager...")
            self.window_manager = WindowManager(
                self.config_manager,
                self.search_engine,
                self.application_manager,
                self.plugin_system
            )
            
            self.logger.info("Initializing HotkeyListener...")
            self.hotkey_listener = HotkeyListener(self.config_manager)
            
            # Step 4: Connect signals
            self._connect_signals()
            
            # Step 5: Start hotkey listener
            self.hotkey_listener.start()
            
            self._initialized = True
            self.logger.info("MainController initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MainController: {e}", exc_info=True)
            raise
    
    def _connect_signals(self):
        """Connect all module signals to main controller"""
        try:
            # Hotkey listener signals
            self.hotkey_listener.hotkey_triggered.connect(self._on_hotkey_triggered)
            
            # Window manager signals
            self.show_window_signal.connect(self.window_manager.show_window)
            self.hide_window_signal.connect(self.window_manager.hide_window)
            
            # Search engine signals
            self.search_request_signal.connect(self.search_engine.search)
            self.search_engine.search_completed.connect(self._on_search_completed)
            
            # Application manager signals
            self.launch_app_signal.connect(self.application_manager.launch_app)
            
            # Plugin system signals
            self.plugin_enable_signal.connect(self.plugin_system.enable_plugin)
            self.plugin_disable_signal.connect(self.plugin_system.disable_plugin)
            self.plugin_click_signal.connect(self.plugin_system.handle_plugin_click)
            
            # Config manager signals
            self.config_change_signal.connect(self.config_manager.update_config)
            self.config_manager.config_updated.connect(self._on_config_updated)
            
            self.logger.info("All signals connected successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to connect signals: {e}", exc_info=True)
            raise
    
    def _on_hotkey_triggered(self):
        """Handle hotkey trigger event"""
        self.logger.debug("Hotkey triggered")
        if self.window_manager.is_visible():
            self.hide_window_signal.emit()
        else:
            self.show_window_signal.emit()
    
    def _on_search_completed(self, results):
        """Handle search completion"""
        self.logger.debug(f"Search completed with {len(results)} results")
        self.search_result_signal.emit(results)
        # Forward to window manager
        self.window_manager.update_search_results(results)
    
    def _on_config_updated(self):
        """Handle configuration update"""
        self.logger.info("Configuration updated, notifying modules...")
        self.config_updated_signal.emit()
        
        # Notify modules to reload their configurations
        if self.hotkey_listener:
            self.hotkey_listener.reload_config()
        if self.window_manager:
            self.window_manager.reload_config()
        if self.search_engine:
            self.search_engine.reload_config()
        if self.application_manager:
            self.application_manager.reload_config()
    
    def shutdown(self):
        """Clean shutdown of all modules"""
        self.logger.info("Shutting down MainController...")
        
        try:
            if self.hotkey_listener:
                self.hotkey_listener.stop()
            if self.window_manager:
                self.window_manager.close()
            if self.plugin_system:
                self.plugin_system.shutdown()
                
            self.logger.info("MainController shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)
