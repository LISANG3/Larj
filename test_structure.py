#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic structure test for Larj
Tests module imports and basic initialization
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all core modules can be imported"""
    print("Testing module imports...")
    
    try:
        from src.core.config_manager import ConfigManager
        print("✓ ConfigManager imported")
        
        from src.core.application_manager import ApplicationManager
        print("✓ ApplicationManager imported")
        
        from src.core.search_engine import SearchEngine
        print("✓ SearchEngine imported")
        
        from src.core.plugin_system import PluginSystem
        print("✓ PluginSystem imported")
        
        from src.core.hotkey_listener import HotkeyListener
        print("✓ HotkeyListener imported")
        
        from src.core.window_manager import WindowManager
        print("✓ WindowManager imported")
        
        from src.core.main_controller import MainController
        print("✓ MainController imported")
        
        from src.ui.main_panel import MainPanel
        print("✓ MainPanel imported")
        
        print("\n✓ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_manager():
    """Test ConfigManager basic functionality"""
    print("\nTesting ConfigManager...")
    
    try:
        from src.core.config_manager import ConfigManager
        
        config = ConfigManager()
        
        # Test get
        trigger_key = config.get("hotkey.trigger_key")
        print(f"  Trigger key: {trigger_key}")
        
        # Test set
        config.set("test.value", "test123")
        value = config.get("test.value")
        assert value == "test123", "Set/Get failed"
        
        print("✓ ConfigManager basic tests passed")
        return True
        
    except Exception as e:
        print(f"✗ ConfigManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plugin_system():
    """Test plugin system basic functionality"""
    print("\nTesting PluginSystem...")
    
    try:
        from src.core.config_manager import ConfigManager
        from src.core.plugin_system import PluginSystem
        
        config = ConfigManager()
        plugin_system = PluginSystem(config)
        
        # Check if sample plugins exist
        from pathlib import Path
        plugin_dir = Path("plugins")
        
        if (plugin_dir / "calculator.py").exists():
            print("  ✓ Calculator plugin found")
        
        if (plugin_dir / "notepad.py").exists():
            print("  ✓ Notepad plugin found")
        
        print("✓ PluginSystem basic tests passed")
        return True
        
    except Exception as e:
        print(f"✗ PluginSystem test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_engine_cache():
    """Test SearchEngine cache path"""
    print("\nTesting SearchEngine cache...")
    
    try:
        from src.core.config_manager import ConfigManager
        from src.core.search_engine import SearchEngine
        
        engine = SearchEngine(ConfigManager())
        results = [{"name": "demo.txt", "path": "C:/demo.txt"}]
        engine._on_search_completed("demo", results)
        
        assert engine._check_cache("demo") is True, "Cache lookup failed"
        print("✓ SearchEngine cache test passed")
        return True
        
    except Exception as e:
        print(f"✗ SearchEngine cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_directory_structure():
    """Test that all required directories exist"""
    print("\nTesting directory structure...")
    
    required_dirs = [
        "src/core",
        "src/ui",
        "src/plugins",
        "src/utils",
        "config",
        "plugins",
        "everything"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        exists = Path(dir_path).exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {dir_path}")
        if not exists:
            all_exist = False
    
    if all_exist:
        print("✓ All required directories exist")
    else:
        print("✗ Some directories are missing")
    
    return all_exist


def main():
    """Run all tests"""
    print("=" * 50)
    print("Larj Structure Test")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Directory Structure", test_directory_structure()))
    results.append(("Module Imports", test_imports()))
    results.append(("ConfigManager", test_config_manager()))
    results.append(("PluginSystem", test_plugin_system()))
    results.append(("SearchEngine Cache", test_search_engine_cache()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Larj structure is ready.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
