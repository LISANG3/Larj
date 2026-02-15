#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plugin System - Extensible plugin architecture
Manages plugin discovery, loading, and lifecycle
"""

import logging
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Any
from PyQt5.QtCore import QObject, pyqtSignal


class PluginBase:
    """
    Base class for all plugins
    All plugins must inherit from this class and implement required methods
    """
    
    def get_name(self) -> str:
        """Get plugin name"""
        raise NotImplementedError
    
    def get_icon(self) -> str:
        """Get plugin icon path or name"""
        raise NotImplementedError
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information (version, author, description)"""
        raise NotImplementedError
    
    def handle_click(self):
        """Handle plugin click event"""
        raise NotImplementedError
    
    # Optional methods
    def on_load(self):
        """Called when plugin is loaded"""
        pass
    
    def on_unload(self):
        """Called when plugin is unloaded"""
        pass
    
    def get_settings(self) -> Dict[str, Any]:
        """Get plugin settings UI configuration"""
        return {}


class PluginSystem(QObject):
    """
    Plugin system - manages plugin lifecycle
    """
    
    # Signals
    plugin_loaded = pyqtSignal(str)  # plugin_name
    plugin_unloaded = pyqtSignal(str)  # plugin_name
    plugin_error = pyqtSignal(str, str)  # plugin_name, error_message
    
    def __init__(self, config_manager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        
        # Plugin directory
        self.plugin_dir = Path(self.config_manager.get("plugin.plugin_directory", "plugins"))
        self.plugin_dir.mkdir(exist_ok=True)
        
        # Loaded plugins
        self.plugins: Dict[str, PluginBase] = {}
        
        # Discover and load enabled plugins
        self._discover_plugins()
        self._load_enabled_plugins()
        
        self.logger.info("PluginSystem initialized")
    
    def _discover_plugins(self):
        """Discover available plugins in plugin directory"""
        try:
            if not self.plugin_dir.exists():
                self.logger.warning(f"Plugin directory not found: {self.plugin_dir}")
                return
            
            # Scan for Python files and package directories
            plugin_files = list(self.plugin_dir.glob("*.py"))
            plugin_files.extend(
                p / "__init__.py"
                for p in self.plugin_dir.iterdir()
                if p.is_dir() and (p / "__init__.py").exists()
            )
            
            self.logger.info(f"Discovered {len(plugin_files)} potential plugin files")
            
            for plugin_file in plugin_files:
                if plugin_file.name.startswith("_"):
                    continue  # Skip private files
                
                self.logger.debug(f"Found plugin file: {plugin_file.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to discover plugins: {e}", exc_info=True)
    
    def _load_enabled_plugins(self):
        """Load plugins that are enabled in configuration"""
        try:
            enabled_plugins = self.config_manager.get("plugin.enabled_plugins", [])
            
            for plugin_name in enabled_plugins:
                self.load_plugin(plugin_name)
            
        except Exception as e:
            self.logger.error(f"Failed to load enabled plugins: {e}")
    
    def load_plugin(self, plugin_name: str) -> bool:
        """Load a plugin by name"""
        try:
            # Check if already loaded
            if plugin_name in self.plugins:
                self.logger.warning(f"Plugin already loaded: {plugin_name}")
                return True
            
            # Find plugin file or package
            plugin_file = self.plugin_dir / f"{plugin_name}.py"
            if not plugin_file.exists():
                plugin_file = self.plugin_dir / plugin_name / "__init__.py"
            
            if not plugin_file.exists():
                self.logger.error(f"Plugin file not found: {plugin_file}")
                return False
            
            # Load module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            if spec is None or spec.loader is None:
                self.logger.error(f"Failed to load plugin spec: {plugin_name}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class (should inherit from PluginBase)
            plugin_class = None
            for item_name in dir(module):
                item = getattr(module, item_name)
                if (isinstance(item, type) and 
                    issubclass(item, PluginBase) and 
                    item != PluginBase):
                    plugin_class = item
                    break
            
            if plugin_class is None:
                self.logger.error(f"No plugin class found in {plugin_name}")
                return False
            
            # Instantiate plugin
            plugin_instance = plugin_class()
            
            # Call on_load if implemented
            if hasattr(plugin_instance, 'on_load'):
                plugin_instance.on_load()
            
            # Store plugin
            self.plugins[plugin_name] = plugin_instance
            
            # Emit signal
            self.plugin_loaded.emit(plugin_name)
            
            self.logger.info(f"Loaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_name}: {e}", exc_info=True)
            self.plugin_error.emit(plugin_name, str(e))
            return False
    
    def unload_plugin(self, plugin_name: str):
        """Unload a plugin"""
        try:
            if plugin_name not in self.plugins:
                self.logger.warning(f"Plugin not loaded: {plugin_name}")
                return
            
            plugin = self.plugins[plugin_name]
            
            # Call on_unload if implemented
            if hasattr(plugin, 'on_unload'):
                plugin.on_unload()
            
            # Remove from loaded plugins
            del self.plugins[plugin_name]
            
            # Emit signal
            self.plugin_unloaded.emit(plugin_name)
            
            self.logger.info(f"Unloaded plugin: {plugin_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to unload plugin {plugin_name}: {e}")
    
    def enable_plugin(self, plugin_name: str):
        """Enable a plugin"""
        try:
            # Load the plugin
            if self.load_plugin(plugin_name):
                # Add to enabled plugins list
                enabled_plugins = self.config_manager.get("plugin.enabled_plugins", [])
                if plugin_name not in enabled_plugins:
                    enabled_plugins.append(plugin_name)
                    self.config_manager.set("plugin.enabled_plugins", enabled_plugins)
                
                self.logger.info(f"Enabled plugin: {plugin_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to enable plugin {plugin_name}: {e}")
    
    def disable_plugin(self, plugin_name: str):
        """Disable a plugin"""
        try:
            # Unload the plugin
            self.unload_plugin(plugin_name)
            
            # Remove from enabled plugins list
            enabled_plugins = self.config_manager.get("plugin.enabled_plugins", [])
            if plugin_name in enabled_plugins:
                enabled_plugins.remove(plugin_name)
                self.config_manager.set("plugin.enabled_plugins", enabled_plugins)
            
            self.logger.info(f"Disabled plugin: {plugin_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to disable plugin {plugin_name}: {e}")
    
    def handle_plugin_click(self, plugin_instance: PluginBase):
        """Handle plugin click event"""
        try:
            plugin_instance.handle_click()
            self.logger.debug(f"Handled click for plugin: {plugin_instance.get_name()}")
            
        except Exception as e:
            plugin_name = plugin_instance.get_name() if hasattr(plugin_instance, 'get_name') else 'unknown'
            self.logger.error(f"Plugin click handler failed for {plugin_name}: {e}", exc_info=True)
            self.plugin_error.emit(plugin_name, str(e))
    
    def get_loaded_plugins(self) -> List[PluginBase]:
        """Get list of loaded plugins"""
        return list(self.plugins.values())
    
    def shutdown(self):
        """Shutdown plugin system and unload all plugins"""
        try:
            plugin_names = list(self.plugins.keys())
            for plugin_name in plugin_names:
                self.unload_plugin(plugin_name)
            
            self.logger.info("Plugin system shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during plugin system shutdown: {e}")
