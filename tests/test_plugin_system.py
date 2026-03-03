#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the refactored plugin system
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5.QtWidgets import QApplication

# Create QApplication before importing modules that use Qt
app = QApplication.instance() or QApplication(sys.argv)

from src.core.plugin_system import PluginBase, PluginSystem
from src.core.config_manager import ConfigManager


class SamplePlugin(PluginBase):
    """A sample plugin for testing"""

    def get_metadata(self) -> dict:
        return {
            "plugin_id": "sample_test",
            "name": "Sample Test Plugin",
            "icon": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "A test plugin",
            "config_schema": {
                "api_key": {"type": "str", "required": True, "desc": "API Key"},
                "region": {"type": "str", "required": False, "default": "us-east", "desc": "Region"}
            }
        }

    def handle_click(self):
        pass

    def apply_settings(self, settings: dict):
        self._settings = settings


class MinimalPlugin(PluginBase):
    """A minimal plugin with no config_schema"""

    def get_metadata(self) -> dict:
        return {
            "plugin_id": "minimal_test",
            "name": "Minimal Plugin",
            "icon": "",
            "version": "0.1.0",
            "author": "",
            "description": "",
            "config_schema": {}
        }

    def handle_click(self):
        pass


@pytest.fixture
def temp_dir():
    """Create temporary directory for test configs"""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def setup_test_env(temp_dir):
    """Set up test environment with plugin and config directories"""
    original_dir = os.getcwd()
    os.chdir(temp_dir)

    # Create plugin directory
    plugin_dir = Path(temp_dir) / "plugins"
    plugin_dir.mkdir()

    # Create config directory
    config_dir = Path(temp_dir) / "config"
    config_dir.mkdir()

    yield temp_dir

    os.chdir(original_dir)


class TestPluginBase:
    """Tests for PluginBase class"""

    def test_get_metadata_returns_dict(self):
        plugin = SamplePlugin()
        metadata = plugin.get_metadata()
        assert isinstance(metadata, dict)
        assert metadata["plugin_id"] == "sample_test"
        assert metadata["name"] == "Sample Test Plugin"
        assert metadata["icon"] == "test"
        assert metadata["version"] == "1.0.0"

    def test_get_metadata_config_schema(self):
        plugin = SamplePlugin()
        metadata = plugin.get_metadata()
        schema = metadata["config_schema"]
        assert "api_key" in schema
        assert schema["api_key"]["type"] == "str"
        assert schema["api_key"]["required"] is True
        assert "region" in schema
        assert schema["region"]["default"] == "us-east"

    def test_minimal_plugin_metadata(self):
        plugin = MinimalPlugin()
        metadata = plugin.get_metadata()
        assert metadata["plugin_id"] == "minimal_test"
        assert metadata["config_schema"] == {}

    def test_apply_settings(self):
        plugin = SamplePlugin()
        plugin.apply_settings({"api_key": "test123", "region": "eu-west"})
        assert plugin._settings["api_key"] == "test123"
        assert plugin._settings["region"] == "eu-west"

    def test_legacy_get_name(self):
        plugin = SamplePlugin()
        assert plugin.get_name() == "Sample Test Plugin"

    def test_legacy_get_icon(self):
        plugin = SamplePlugin()
        assert plugin.get_icon() == "test"


class TestPluginSystem:
    """Tests for PluginSystem class"""

    def test_initialization(self, setup_test_env):
        config_manager = ConfigManager()
        plugin_system = PluginSystem(config_manager)
        assert plugin_system.plugins == {}
        assert plugin_system.discovered_plugins == {}

    def test_discover_single_file_plugin(self, setup_test_env):
        # Write a test plugin file
        plugin_code = '''
from src.core.plugin_system import PluginBase

class TestFilePlugin(PluginBase):
    def get_metadata(self):
        return {
            "plugin_id": "test_file",
            "name": "Test File Plugin",
            "icon": "file",
            "version": "1.0.0",
            "author": "Test",
            "description": "A file plugin",
            "config_schema": {}
        }
    def handle_click(self):
        pass
'''
        plugin_path = Path(setup_test_env) / "plugins" / "test_file.py"
        plugin_path.write_text(plugin_code)

        # Add project root to sys.path for import
        project_root = str(Path(__file__).parent.parent)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        config_manager = ConfigManager()
        plugin_system = PluginSystem(config_manager)

        assert "test_file" in plugin_system.discovered_plugins
        metadata = plugin_system.discovered_plugins["test_file"]["metadata"]
        assert metadata["name"] == "Test File Plugin"

    def test_discover_directory_plugin(self, setup_test_env):
        # Write a test plugin package
        plugin_dir = Path(setup_test_env) / "plugins" / "test_pkg"
        plugin_dir.mkdir()

        plugin_code = '''
from src.core.plugin_system import PluginBase

class TestPkgPlugin(PluginBase):
    def get_metadata(self):
        return {
            "plugin_id": "test_pkg",
            "name": "Test Package Plugin",
            "icon": "pkg",
            "version": "2.0.0",
            "author": "Test",
            "description": "A package plugin",
            "config_schema": {
                "token": {"type": "str", "required": True, "desc": "Auth token"}
            }
        }
    def handle_click(self):
        pass
    def apply_settings(self, settings):
        self._settings = settings
'''
        (plugin_dir / "__init__.py").write_text(plugin_code)

        config_manager = ConfigManager()
        plugin_system = PluginSystem(config_manager)

        assert "test_pkg" in plugin_system.discovered_plugins
        metadata = plugin_system.discovered_plugins["test_pkg"]["metadata"]
        assert metadata["name"] == "Test Package Plugin"
        assert "token" in metadata["config_schema"]

    def test_default_config_generated(self, setup_test_env):
        plugin_code = '''
from src.core.plugin_system import PluginBase

class ConfigPlugin(PluginBase):
    def get_metadata(self):
        return {
            "plugin_id": "config_test",
            "name": "Config Test",
            "icon": "",
            "version": "1.0.0",
            "author": "",
            "description": "",
            "config_schema": {
                "api_key": {"type": "str", "required": True, "desc": "Key"},
                "region": {"type": "str", "required": False, "default": "us-east", "desc": "Region"}
            }
        }
    def handle_click(self):
        pass
'''
        plugin_path = Path(setup_test_env) / "plugins" / "config_test.py"
        plugin_path.write_text(plugin_code)

        config_manager = ConfigManager()
        plugin_system = PluginSystem(config_manager)

        # Check that config file was auto-generated
        config_file = Path(setup_test_env) / "config" / "plugins" / "config_test.json"
        assert config_file.exists()

        with open(config_file, 'r') as f:
            config = json.load(f)
        assert config["region"] == "us-east"
        assert config["api_key"] == ""  # No default, so empty string

    def test_load_enabled_plugin(self, setup_test_env):
        plugin_code = '''
from src.core.plugin_system import PluginBase

class LoadTestPlugin(PluginBase):
    def get_metadata(self):
        return {
            "plugin_id": "load_test",
            "name": "Load Test",
            "icon": "",
            "version": "1.0.0",
            "author": "",
            "description": "",
            "config_schema": {}
        }
    def handle_click(self):
        pass
'''
        plugin_path = Path(setup_test_env) / "plugins" / "load_test.py"
        plugin_path.write_text(plugin_code)

        # Set enabled_plugins in settings
        settings_file = Path(setup_test_env) / "config" / "settings.json"
        settings_file.parent.mkdir(exist_ok=True)
        with open(settings_file, 'w') as f:
            json.dump({"plugin": {"enabled_plugins": ["load_test"], "plugin_directory": "plugins"}}, f)

        config_manager = ConfigManager()
        plugin_system = PluginSystem(config_manager)

        assert "load_test" in plugin_system.plugins
        assert "load_test" in plugin_system.discovered_plugins

    def test_enable_disable_plugin(self, setup_test_env):
        plugin_code = '''
from src.core.plugin_system import PluginBase

class TogglePlugin(PluginBase):
    def get_metadata(self):
        return {
            "plugin_id": "toggle_test",
            "name": "Toggle Test",
            "icon": "",
            "version": "1.0.0",
            "author": "",
            "description": "",
            "config_schema": {}
        }
    def handle_click(self):
        pass
'''
        plugin_path = Path(setup_test_env) / "plugins" / "toggle_test.py"
        plugin_path.write_text(plugin_code)

        config_manager = ConfigManager()
        plugin_system = PluginSystem(config_manager)

        # Enable
        plugin_system.enable_plugin("toggle_test")
        assert "toggle_test" in plugin_system.plugins
        assert "toggle_test" in config_manager.get("plugin.enabled_plugins", [])

        # Disable
        plugin_system.disable_plugin("toggle_test")
        assert "toggle_test" not in plugin_system.plugins
        assert "toggle_test" not in config_manager.get("plugin.enabled_plugins", [])

    def test_plugin_config_read_write(self, setup_test_env):
        config_manager = ConfigManager()
        plugin_system = PluginSystem(config_manager)

        # Write config
        plugin_system.set_plugin_config("my_plugin", {"key1": "val1", "key2": "val2"})

        # Read config
        config = plugin_system.get_plugin_config("my_plugin")
        assert config["key1"] == "val1"
        assert config["key2"] == "val2"

        # Update config
        plugin_system.set_plugin_config("my_plugin", {"key2": "updated"})
        config = plugin_system.get_plugin_config("my_plugin")
        assert config["key1"] == "val1"
        assert config["key2"] == "updated"

    def test_plugin_isolation_on_error(self, setup_test_env):
        """Plugin errors should not crash the system"""
        plugin_code = '''
from src.core.plugin_system import PluginBase

class ErrorPlugin(PluginBase):
    def get_metadata(self):
        return {
            "plugin_id": "error_test",
            "name": "Error Test",
            "icon": "",
            "version": "1.0.0",
            "author": "",
            "description": "",
            "config_schema": {}
        }
    def handle_click(self):
        raise RuntimeError("Plugin error!")
    def on_load(self):
        raise RuntimeError("Load error!")
'''
        plugin_path = Path(setup_test_env) / "plugins" / "error_test.py"
        plugin_path.write_text(plugin_code)

        settings_file = Path(setup_test_env) / "config" / "settings.json"
        settings_file.parent.mkdir(exist_ok=True)
        with open(settings_file, 'w') as f:
            json.dump({"plugin": {"enabled_plugins": ["error_test"], "plugin_directory": "plugins"}}, f)

        config_manager = ConfigManager()
        # Should not raise even though on_load fails
        plugin_system = PluginSystem(config_manager)
        assert "error_test" in plugin_system.plugins

        # handle_click should not crash
        plugin = plugin_system.plugins["error_test"]
        plugin_system.handle_plugin_click(plugin)

    def test_duplicate_plugin_id_skipped(self, setup_test_env):
        """Duplicate plugin_id from different files should be skipped"""
        plugin_code1 = '''
from src.core.plugin_system import PluginBase

class DupPlugin1(PluginBase):
    def get_metadata(self):
        return {
            "plugin_id": "dup_id",
            "name": "Dup 1",
            "icon": "",
            "version": "1.0.0",
            "author": "",
            "description": "",
            "config_schema": {}
        }
    def handle_click(self):
        pass
'''
        plugin_code2 = '''
from src.core.plugin_system import PluginBase

class DupPlugin2(PluginBase):
    def get_metadata(self):
        return {
            "plugin_id": "dup_id",
            "name": "Dup 2",
            "icon": "",
            "version": "2.0.0",
            "author": "",
            "description": "",
            "config_schema": {}
        }
    def handle_click(self):
        pass
'''
        (Path(setup_test_env) / "plugins" / "dup_a.py").write_text(plugin_code1)
        (Path(setup_test_env) / "plugins" / "dup_b.py").write_text(plugin_code2)

        config_manager = ConfigManager()
        plugin_system = PluginSystem(config_manager)

        # Only first one should be discovered
        assert "dup_id" in plugin_system.discovered_plugins
        # Only one should exist
        count = sum(1 for pid in plugin_system.discovered_plugins if pid == "dup_id")
        assert count == 1

    def test_get_discovered_plugins(self, setup_test_env):
        plugin_code = '''
from src.core.plugin_system import PluginBase

class DiscoverTestPlugin(PluginBase):
    def get_metadata(self):
        return {
            "plugin_id": "discover_test",
            "name": "Discover Test",
            "icon": "test",
            "version": "1.0.0",
            "author": "Tester",
            "description": "Test description",
            "config_schema": {}
        }
    def handle_click(self):
        pass
'''
        plugin_path = Path(setup_test_env) / "plugins" / "discover_test.py"
        plugin_path.write_text(plugin_code)

        config_manager = ConfigManager()
        plugin_system = PluginSystem(config_manager)

        discovered = plugin_system.get_discovered_plugins()
        assert "discover_test" in discovered
        assert discovered["discover_test"]["name"] == "Discover Test"
        assert discovered["discover_test"]["author"] == "Tester"

    def test_migrate_old_config(self, setup_test_env):
        """Test migration from old plugins.json format"""
        config_dir = Path(setup_test_env) / "config"
        config_dir.mkdir(exist_ok=True)

        # Create old-style plugins.json
        old_data = {
            "plugins": {
                "my_old_plugin": {
                    "api_key": "old_key_value",
                    "region": "ap-guangzhou"
                }
            }
        }
        with open(config_dir / "plugins.json", 'w') as f:
            json.dump(old_data, f)

        config_manager = ConfigManager()
        plugin_system = PluginSystem(config_manager)

        # Check migrated config
        migrated_config = plugin_system.get_plugin_config("my_old_plugin")
        assert migrated_config["api_key"] == "old_key_value"
        assert migrated_config["region"] == "ap-guangzhou"

        # Check old data was cleared
        with open(config_dir / "plugins.json", 'r') as f:
            old_data_after = json.load(f)
        assert old_data_after["plugins"] == {}

    def test_shutdown_unloads_all(self, setup_test_env):
        plugin_code = '''
from src.core.plugin_system import PluginBase

class ShutdownPlugin(PluginBase):
    def get_metadata(self):
        return {
            "plugin_id": "shutdown_test",
            "name": "Shutdown Test",
            "icon": "",
            "version": "1.0.0",
            "author": "",
            "description": "",
            "config_schema": {}
        }
    def handle_click(self):
        pass
'''
        plugin_path = Path(setup_test_env) / "plugins" / "shutdown_test.py"
        plugin_path.write_text(plugin_code)

        settings_file = Path(setup_test_env) / "config" / "settings.json"
        settings_file.parent.mkdir(exist_ok=True)
        with open(settings_file, 'w') as f:
            json.dump({"plugin": {"enabled_plugins": ["shutdown_test"], "plugin_directory": "plugins"}}, f)

        config_manager = ConfigManager()
        plugin_system = PluginSystem(config_manager)

        assert "shutdown_test" in plugin_system.plugins
        plugin_system.shutdown()
        assert len(plugin_system.plugins) == 0


class TestExistingPlugins:
    """Test that existing plugins work with the new system"""

    def test_calculator_metadata(self):
        from plugins.calculator import CalculatorPlugin
        plugin = CalculatorPlugin()
        metadata = plugin.get_metadata()
        assert metadata["plugin_id"] == "calculator"
        assert metadata["name"] == "Calculator"
        assert metadata["icon"] == "calculator"
        assert metadata["config_schema"] == {}

    def test_ocr_metadata(self):
        from plugins.ocr import TencentOcrPlugin
        plugin = TencentOcrPlugin()
        metadata = plugin.get_metadata()
        assert metadata["plugin_id"] == "ocr"
        assert metadata["name"] == "OCR 识别"
        assert metadata["icon"] == "scan"
        schema = metadata["config_schema"]
        assert "secret_id" in schema
        assert "secret_key" in schema
        assert "region" in schema
        assert schema["region"]["default"] == "ap-beijing"

    def test_mtran_metadata(self):
        from plugins.mtran_server import TencentTranslationPlugin
        plugin = TencentTranslationPlugin()
        metadata = plugin.get_metadata()
        assert metadata["plugin_id"] == "mtran_server"
        assert metadata["name"] == "腾讯翻译"
        assert metadata["icon"] == "translate"
        schema = metadata["config_schema"]
        assert "secret_id" in schema
        assert "secret_key" in schema
        assert "region" in schema

    def test_ocr_apply_settings(self):
        from plugins.ocr import TencentOcrPlugin
        plugin = TencentOcrPlugin()
        plugin.apply_settings({
            "secret_id": "test_id",
            "secret_key": "test_key",
            "region": "ap-shanghai"
        })
        assert plugin.get_secret_id() == "test_id"
        assert plugin.get_secret_key() == "test_key"
        assert plugin.get_region() == "ap-shanghai"

    def test_mtran_apply_settings(self):
        from plugins.mtran_server import TencentTranslationPlugin
        plugin = TencentTranslationPlugin()
        plugin.apply_settings({
            "secret_id": "test_id",
            "secret_key": "test_key",
            "region": "ap-shanghai"
        })
        assert plugin.get_secret_id() == "test_id"
        assert plugin.get_secret_key() == "test_key"
        assert plugin.get_region() == "ap-shanghai"
