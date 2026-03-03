#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Manager - Unified configuration storage and access
Handles configuration file read/write, validation, and hot reload
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict
from PyQt5.QtCore import QObject, pyqtSignal


class ConfigManager(QObject):
    """
    Configuration manager - handles all configuration data
    """
    
    # Signal emitted when configuration is updated
    config_updated = pyqtSignal()
    
    # Default configuration values
    DEFAULT_CONFIG = {
        "hotkey": {
            "trigger_key": "XButton1",  # Mouse side button
            "fallback_keys": ["Ctrl+Space"],
            "enabled": True
        },
        "window": {
            "width": 600,
            "height": 400,
            "opacity": 95,
            "corner_radius": 10,
            "follow_mouse": True,
            "animation_duration": 200
        },
        "search": {
            "max_results": 50,
            "debounce_ms": 300,
            "es_path": "everything/es.exe",
            "search_paths": [],
            "exclude_paths": [],
            "cache_timeout": 60
        },
        "application": {
            "auto_sort": True,
            "sort_by": "usage",  # usage, name, date
            "groups": []
        },
        "plugin": {
            "enabled_plugins": [],
            "plugin_directory": "plugins"
        },
        "appearance": {
            "background_type": "gradient",
            "background_gradient_start": "#f8fafc",
            "background_gradient_end": "#f1f5f9",
            "background_color": "#f8fafc",
            "background_image": "",
            "accent_color": "#3b82f6"
        }
    }
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Config directories
        self.config_dir = Path("config")
        self.config_dir.mkdir(exist_ok=True)
        
        # Per-plugin config directory
        self.plugins_config_dir = self.config_dir / "plugins"
        self.plugins_config_dir.mkdir(exist_ok=True)
        
        # Config files
        self.settings_file = self.config_dir / "settings.json"
        self.apps_file = self.config_dir / "apps.json"
        self.plugins_file = self.config_dir / "plugins.json"
        
        # Load configurations
        self.settings = self._load_or_create(self.settings_file, self.DEFAULT_CONFIG)
        self.apps = self._load_or_create(self.apps_file, {"apps": []})
        self.plugins = self._load_or_create(self.plugins_file, {"plugins": {}})
        
        self.logger.info("ConfigManager initialized")
    
    def _load_or_create(self, file_path: Path, default_data: Dict) -> Dict:
        """Load config file or create with defaults if not exists"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.logger.info(f"Loaded config from {file_path}")
                    return data
            else:
                # Create default config
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
                self.logger.info(f"Created default config at {file_path}")
                return default_data
                
        except Exception as e:
            self.logger.error(f"Failed to load config from {file_path}: {e}")
            return default_data
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by key path (e.g., "window.width")
        """
        try:
            keys = key_path.split('.')
            value = self.settings
            
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return default
                    
            return value if value is not None else default
            
        except Exception as e:
            self.logger.error(f"Failed to get config value for {key_path}: {e}")
            return default
    
    def set(self, key_path: str, value: Any):
        """
        Set configuration value by key path (e.g., "window.width")
        """
        try:
            keys = key_path.split('.')
            config = self.settings
            
            # Navigate to the parent dict
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # Set the value
            config[keys[-1]] = value
            
            # Save to file
            self._save_settings()
            self.config_updated.emit()
            
            self.logger.debug(f"Config updated: {key_path} = {value}")
            
        except Exception as e:
            self.logger.error(f"Failed to set config value for {key_path}: {e}")
    
    def _save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            self.logger.debug("Settings saved")
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
    
    def save_apps(self):
        """Save application data to file"""
        try:
            with open(self.apps_file, 'w', encoding='utf-8') as f:
                json.dump(self.apps, f, indent=2, ensure_ascii=False)
            self.logger.debug("Apps data saved")
        except Exception as e:
            self.logger.error(f"Failed to save apps data: {e}")
    
    def save_plugins(self):
        """Save plugin data to file"""
        try:
            with open(self.plugins_file, 'w', encoding='utf-8') as f:
                json.dump(self.plugins, f, indent=2, ensure_ascii=False)
            self.logger.debug("Plugins data saved")
        except Exception as e:
            self.logger.error(f"Failed to save plugins data: {e}")
    
    def update_config(self, config_data: Dict):
        """Update configuration with new data"""
        try:
            self.settings.update(config_data)
            self._save_settings()
            self.config_updated.emit()
            self.logger.info("Configuration updated")
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
    
    def get_apps(self) -> list:
        """Get list of applications"""
        return self.apps.get("apps", [])
    
    def add_app(self, app_data: Dict):
        """Add new application"""
        try:
            if "apps" not in self.apps:
                self.apps["apps"] = []
            
            self.apps["apps"].append(app_data)
            self.save_apps()
            self.logger.info(f"Added app: {app_data.get('name')}")
            
        except Exception as e:
            self.logger.error(f"Failed to add app: {e}")
    
    def remove_app(self, app_id: str):
        """Remove application by ID"""
        try:
            apps = self.apps.get("apps", [])
            self.apps["apps"] = [app for app in apps if app.get("id") != app_id]
            self.save_apps()
            self.logger.info(f"Removed app: {app_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to remove app: {e}")
    
    def update_app(self, app_id: str, app_data: Dict):
        """Update application data"""
        try:
            apps = self.apps.get("apps", [])
            for i, app in enumerate(apps):
                if app.get("id") == app_id:
                    apps[i].update(app_data)
                    break
            
            self.save_apps()
            self.logger.info(f"Updated app: {app_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update app: {e}")
