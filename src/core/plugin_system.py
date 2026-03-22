#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plugin System - Extensible plugin architecture
Manages plugin discovery, loading, and lifecycle
Plugins are auto-discovered from the plugins/ directory and expose metadata via get_metadata()
"""

import json
import logging
import importlib.util
import os
import tempfile
from pathlib import Path
from typing import Dict, List
from PyQt5.QtCore import QObject, pyqtSignal


class PluginBase:
    """
    Base class for all plugins
    All plugins must inherit from this class and implement get_metadata() and handle_click()
    """

    def get_metadata(self) -> dict:
        """
        Get plugin metadata. Plugins must override this method to provide:
        - plugin_id: str - Unique identifier (matches filename/directory name)
        - name: str - Display name
        - icon: str - Icon identifier
        - version: str - Version string
        - author: str - Author name
        - description: str - Plugin description
        - config_schema: dict - Configuration schema for auto-generating config forms
            Each key maps to: {"type": "str", "required": bool, "default": any, "desc": str}
        """
        raise NotImplementedError("Plugins must implement get_metadata()")

    def handle_click(self):
        """Handle plugin click event"""
        raise NotImplementedError

    # Optional lifecycle methods
    def on_load(self):
        """Called when plugin is loaded"""
        pass

    def on_unload(self):
        """Called when plugin is unloaded"""
        pass

    def apply_settings(self, settings: dict):
        """Apply configuration settings to the plugin"""
        pass


class PluginSystem(QObject):
    """
    Plugin system - manages plugin lifecycle with auto-discovery
    Plugins are automatically discovered from the plugins/ directory.
    Plugin metadata and config_schema are read from plugins themselves.
    Per-plugin configuration is stored in config/plugins/[plugin_id].json
    """

    # Signals
    plugin_loaded = pyqtSignal(str)  # plugin_id
    plugin_unloaded = pyqtSignal(str)  # plugin_id
    plugin_error = pyqtSignal(str, str)  # plugin_id, error_message

    def __init__(self, config_manager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # Plugin directory
        self.plugin_dir = Path(self.config_manager.get("plugin.plugin_directory", "plugins"))
        self.plugin_dir.mkdir(exist_ok=True)

        # Per-plugin config directory
        self.plugin_config_dir = Path("config") / "plugins"
        self.plugin_config_dir.mkdir(parents=True, exist_ok=True)

        # Discovered plugins: {plugin_id: {"metadata": dict, "class": type, "module": module, "file": Path}}
        self.discovered_plugins: Dict[str, dict] = {}

        # Loaded (active) plugin instances: {plugin_id: PluginBase}
        self.plugins: Dict[str, PluginBase] = {}

        # Migrate old plugin config if needed
        self._migrate_old_config()

        # Discover and load enabled plugins
        self._discover_plugins()
        self._load_enabled_plugins()

        self.logger.info("PluginSystem initialized")

    def _migrate_old_config(self):
        """Migrate old config/plugins.json data to per-plugin config files"""
        try:
            old_plugins_file = Path("config") / "plugins.json"
            if not old_plugins_file.exists():
                return

            with open(old_plugins_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)

            plugins_data = old_data.get("plugins", {})
            if not plugins_data:
                return

            for plugin_id, plugin_config in plugins_data.items():
                if not isinstance(plugin_config, dict):
                    continue
                config_file = self.plugin_config_dir / f"{plugin_id}.json"
                if not config_file.exists():
                    self._atomic_write_json(config_file, plugin_config)
                    self.logger.info(f"Migrated config for plugin: {plugin_id}")

            # Clear old plugins node after migration
            old_data["plugins"] = {}
            self._atomic_write_json(old_plugins_file, old_data)
            self.logger.info("Old plugin config migration complete")

        except Exception as e:
            self.logger.error(f"Failed to migrate old plugin config: {e}", exc_info=True)

    def _discover_plugins(self):
        """Discover all available plugins in plugin directory and extract metadata"""
        try:
            if not self.plugin_dir.exists():
                self.logger.warning(f"Plugin directory not found: {self.plugin_dir}")
                return

            # Collect plugin candidates
            plugin_candidates = []

            # Single-file plugins: plugins/xxx.py (skip __init__.py and private files)
            for py_file in self.plugin_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                plugin_name = py_file.stem
                plugin_candidates.append((plugin_name, py_file))

            # Directory plugins: plugins/xxx/__init__.py
            for subdir in self.plugin_dir.iterdir():
                if not subdir.is_dir() or subdir.name.startswith("_"):
                    continue
                init_file = subdir / "__init__.py"
                if init_file.exists():
                    plugin_candidates.append((subdir.name, init_file))

            self.logger.info(f"Found {len(plugin_candidates)} potential plugin(s)")

            for plugin_name, plugin_file in plugin_candidates:
                try:
                    self._discover_single_plugin(plugin_name, plugin_file)
                except Exception as e:
                    self.logger.error(f"Failed to discover plugin '{plugin_name}': {e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Failed to discover plugins: {e}", exc_info=True)

    def _discover_single_plugin(self, plugin_name: str, plugin_file: Path):
        """Import a single plugin module and extract its metadata"""
        module_name = f"plugins.{plugin_name}"

        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        if spec is None or spec.loader is None:
            self.logger.warning(f"Cannot create module spec for: {plugin_name}")
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find plugin class (must inherit from PluginBase)
        plugin_class = None
        for item_name in dir(module):
            item = getattr(module, item_name)
            if (isinstance(item, type) and
                    issubclass(item, PluginBase) and
                    item is not PluginBase):
                plugin_class = item
                break

        if plugin_class is None:
            self.logger.warning(f"No PluginBase subclass found in '{plugin_name}', skipping")
            return

        # Check that get_metadata is available
        if not hasattr(plugin_class, 'get_metadata') or not callable(getattr(plugin_class, 'get_metadata', None)):
            self.logger.warning(f"Plugin '{plugin_name}' does not implement get_metadata, skipping")
            return

        # Prefer class-level metadata call to avoid discovery-time instantiation cost.
        metadata = None
        class_get_metadata = getattr(plugin_class, "get_metadata", None)
        if callable(class_get_metadata):
            try:
                metadata = class_get_metadata()
            except TypeError:
                metadata = None
            except Exception as e:
                self.logger.error(
                    f"Failed to read class metadata for plugin '{plugin_name}': {e}",
                    exc_info=True
                )
                return

        if metadata is None:
            try:
                temp_instance = plugin_class()
                metadata = temp_instance.get_metadata()
            except Exception as e:
                self.logger.error(f"Failed to instantiate plugin class in '{plugin_name}': {e}", exc_info=True)
                return

        if not isinstance(metadata, dict) or "plugin_id" not in metadata:
            self.logger.warning(f"Plugin '{plugin_name}' returned invalid metadata, skipping")
            return

        plugin_id = metadata["plugin_id"]

        # Avoid duplicate plugin_id
        if plugin_id in self.discovered_plugins:
            self.logger.warning(f"Duplicate plugin_id '{plugin_id}' from '{plugin_name}', skipping")
            return

        self.discovered_plugins[plugin_id] = {
            "metadata": metadata,
            "class": plugin_class,
            "file": plugin_file,
        }

        # Auto-generate default config file if not exists
        self._ensure_plugin_config(plugin_id, metadata.get("config_schema", {}))

        self.logger.info(f"Discovered plugin: {plugin_id} ({metadata.get('name', plugin_id)})")

    def _ensure_plugin_config(self, plugin_id: str, config_schema: dict):
        """Create default config file for a plugin if it doesn't exist"""
        config_file = self.plugin_config_dir / f"{plugin_id}.json"
        if config_file.exists():
            return

        default_config = {}
        for key, schema in config_schema.items():
            if "default" in schema:
                default_config[key] = schema["default"]
            else:
                default_config[key] = ""

        self._atomic_write_json(config_file, default_config)
        self.logger.debug(f"Created default config for plugin: {plugin_id}")

    def _load_enabled_plugins(self):
        """Load plugins that are enabled in configuration"""
        try:
            enabled_plugins = self.config_manager.get("plugin.enabled_plugins", [])

            for plugin_id in enabled_plugins:
                if plugin_id in self.discovered_plugins:
                    self.load_plugin(plugin_id)
                else:
                    self.logger.warning(f"Enabled plugin '{plugin_id}' not found in discovered plugins")

        except Exception as e:
            self.logger.error(f"Failed to load enabled plugins: {e}")

    def load_plugin(self, plugin_id: str) -> bool:
        """Load a plugin by its plugin_id"""
        try:
            # Check if already loaded
            if plugin_id in self.plugins:
                self.logger.warning(f"Plugin already loaded: {plugin_id}")
                return True

            # Must be discovered first
            if plugin_id not in self.discovered_plugins:
                self.logger.error(f"Plugin not discovered: {plugin_id}")
                return False

            discovery_info = self.discovered_plugins[plugin_id]
            plugin_class = discovery_info["class"]
            metadata = discovery_info["metadata"]

            # Instantiate plugin
            plugin_instance = plugin_class()

            # Load saved config and apply
            config_schema = metadata.get("config_schema", {})
            if config_schema:
                saved_config = self.get_plugin_config(plugin_id)
                if saved_config and hasattr(plugin_instance, 'apply_settings'):
                    plugin_instance.apply_settings(saved_config)

            # Call on_load
            try:
                plugin_instance.on_load()
            except Exception as e:
                self.logger.error(f"Plugin '{plugin_id}' on_load failed: {e}", exc_info=True)

            # Store plugin
            self.plugins[plugin_id] = plugin_instance

            # Emit signal
            self.plugin_loaded.emit(plugin_id)

            self.logger.info(f"Loaded plugin: {plugin_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_id}: {e}", exc_info=True)
            self.plugin_error.emit(plugin_id, str(e))
            return False

    def unload_plugin(self, plugin_id: str):
        """Unload a plugin"""
        try:
            if plugin_id not in self.plugins:
                self.logger.warning(f"Plugin not loaded: {plugin_id}")
                return

            plugin = self.plugins[plugin_id]

            # Call on_unload
            try:
                plugin.on_unload()
            except Exception as e:
                self.logger.error(f"Plugin '{plugin_id}' on_unload failed: {e}", exc_info=True)

            # Remove from loaded plugins
            del self.plugins[plugin_id]

            # Emit signal
            self.plugin_unloaded.emit(plugin_id)

            self.logger.info(f"Unloaded plugin: {plugin_id}")

        except Exception as e:
            self.logger.error(f"Failed to unload plugin {plugin_id}: {e}")

    def enable_plugin(self, plugin_id: str):
        """Enable a plugin"""
        try:
            if self.load_plugin(plugin_id):
                enabled_plugins = self.config_manager.get("plugin.enabled_plugins", [])
                if plugin_id not in enabled_plugins:
                    enabled_plugins.append(plugin_id)
                    self.config_manager.set("plugin.enabled_plugins", enabled_plugins)

                self.logger.info(f"Enabled plugin: {plugin_id}")

        except Exception as e:
            self.logger.error(f"Failed to enable plugin {plugin_id}: {e}")

    def disable_plugin(self, plugin_id: str):
        """Disable a plugin"""
        try:
            self.unload_plugin(plugin_id)

            enabled_plugins = self.config_manager.get("plugin.enabled_plugins", [])
            if plugin_id in enabled_plugins:
                enabled_plugins.remove(plugin_id)
                self.config_manager.set("plugin.enabled_plugins", enabled_plugins)

            self.logger.info(f"Disabled plugin: {plugin_id}")

        except Exception as e:
            self.logger.error(f"Failed to disable plugin {plugin_id}: {e}")

    def handle_plugin_click(self, plugin_instance: PluginBase):
        """Handle plugin click event with isolation"""
        try:
            plugin_instance.handle_click()
            metadata = plugin_instance.get_metadata()
            self.logger.debug(f"Handled click for plugin: {metadata.get('name', 'unknown')}")

        except Exception as e:
            try:
                plugin_name = plugin_instance.get_metadata().get("name", "unknown")
            except Exception:
                plugin_name = "unknown"
            self.logger.error(f"Plugin click handler failed for {plugin_name}: {e}", exc_info=True)
            self.plugin_error.emit(plugin_name, str(e))

    def get_loaded_plugins(self) -> List[PluginBase]:
        """Get list of loaded plugin instances"""
        return list(self.plugins.values())

    def get_discovered_plugins(self) -> Dict[str, dict]:
        """Get metadata for all discovered plugins: {plugin_id: metadata_dict}"""
        return {pid: info["metadata"] for pid, info in self.discovered_plugins.items()}

    def get_plugin_config(self, plugin_id: str) -> dict:
        """Read per-plugin configuration from config/plugins/[plugin_id].json"""
        config_file = self.plugin_config_dir / f"{plugin_id}.json"
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read config for plugin '{plugin_id}': {e}")
        return {}

    def set_plugin_config(self, plugin_id: str, config_data: dict):
        """Write per-plugin configuration to config/plugins/[plugin_id].json (atomic)"""
        config_file = self.plugin_config_dir / f"{plugin_id}.json"
        try:
            # Merge with existing config
            existing = self.get_plugin_config(plugin_id)
            existing.update(config_data)
            self._atomic_write_json(config_file, existing)
            self.logger.debug(f"Saved config for plugin: {plugin_id}")
        except Exception as e:
            self.logger.error(f"Failed to save config for plugin '{plugin_id}': {e}")

    def _atomic_write_json(self, file_path: Path, data: dict):
        """Write JSON atomically using temp file + rename"""
        dir_path = file_path.parent
        try:
            fd, tmp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".json.tmp")
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                # Atomic rename
                os.replace(tmp_path, str(file_path))
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            self.logger.error(f"Atomic write failed for {file_path}: {e}")
            raise

    def shutdown(self):
        """Shutdown plugin system and unload all plugins"""
        try:
            plugin_ids = list(self.plugins.keys())
            for plugin_id in plugin_ids:
                try:
                    self.unload_plugin(plugin_id)
                except Exception as e:
                    self.logger.error(f"Error unloading plugin '{plugin_id}' during shutdown: {e}")

            self.discovered_plugins.clear()
            self.logger.info("Plugin system shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during plugin system shutdown: {e}")
