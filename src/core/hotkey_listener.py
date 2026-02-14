#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hotkey Listener - Global hotkey monitoring
Monitors mouse buttons and keyboard shortcuts to trigger the panel
"""

import logging
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from pynput import mouse, keyboard as pynput_keyboard


class HotkeyListener(QObject):
    """
    Hotkey listener - monitors global input for trigger events
    Supports both mouse buttons (XButton1/2) and keyboard shortcuts
    """
    
    # Signal emitted when hotkey is triggered
    hotkey_triggered = pyqtSignal()
    
    def __init__(self, config_manager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        
        # Listeners
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # State
        self.enabled = True
        self.last_trigger_time = 0
        self.debounce_ms = 200  # Prevent double-triggers
        self.pressed_keys = set()
        
        # Load configuration
        self.reload_config()
        
        self.logger.info("HotkeyListener initialized")
    
    def reload_config(self):
        """Reload configuration"""
        try:
            self.trigger_key = self.config_manager.get("hotkey.trigger_key", "XButton1")
            self.fallback_keys = self.config_manager.get("hotkey.fallback_keys", ["Ctrl+Space"])
            self.enabled = self.config_manager.get("hotkey.enabled", True)
            
            self.logger.info(f"Hotkey config reloaded: {self.trigger_key}, fallback: {self.fallback_keys}")
            
        except Exception as e:
            self.logger.error(f"Failed to reload hotkey config: {e}")
    
    def start(self):
        """Start listening for hotkey events"""
        try:
            # Start mouse listener
            self.mouse_listener = mouse.Listener(
                on_click=self._on_mouse_click
            )
            self.mouse_listener.start()
            
            # Start keyboard listener for fallback keys
            self.keyboard_listener = pynput_keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self.keyboard_listener.start()
            
            self.logger.info("Hotkey listeners started")
            
        except Exception as e:
            self.logger.error(f"Failed to start hotkey listener: {e}", exc_info=True)
    
    def stop(self):
        """Stop listening for hotkey events"""
        try:
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None
            
            if self.keyboard_listener:
                self.keyboard_listener.stop()
                self.keyboard_listener = None
            self.pressed_keys.clear()
            
            self.logger.info("Hotkey listeners stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop hotkey listener: {e}")
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click event"""
        if not self.enabled or not pressed:
            return
        
        try:
            # Check if it's the trigger button
            button_name = button.name if hasattr(button, 'name') else str(button)
            
            # XButton1 is mouse button 8 (side button)
            # XButton2 is mouse button 9 (side button)
            if button_name in ['x1', 'x2'] and self.trigger_key in ['XButton1', 'XButton2']:
                expected_button = 'x1' if self.trigger_key == 'XButton1' else 'x2'
                if button_name != expected_button:
                    return
            elif self.trigger_key not in ['XButton1', 'XButton2']:
                return

            if self._check_debounce():
                self.logger.debug(f"Mouse button {button_name} triggered")
                self.hotkey_triggered.emit()
                    
        except Exception as e:
            self.logger.error(f"Error handling mouse click: {e}")
    
    def _on_key_press(self, key):
        """Handle keyboard key press"""
        if not self.enabled:
            return
        
        try:
            key_name = self._normalize_key(key)
            if not key_name:
                return

            self.pressed_keys.add(key_name)

            for shortcut in self.fallback_keys:
                required_keys = {part.strip().lower() for part in shortcut.split('+') if part.strip()}
                if required_keys and required_keys.issubset(self.pressed_keys):
                    if self._check_debounce():
                        self.logger.debug(f"Keyboard shortcut {shortcut} triggered")
                        self.hotkey_triggered.emit()
                    break
            
        except Exception as e:
            self.logger.error(f"Error handling key press: {e}")

    def _on_key_release(self, key):
        """Handle keyboard key release"""
        try:
            key_name = self._normalize_key(key)
            if key_name:
                self.pressed_keys.discard(key_name)
        except Exception as e:
            self.logger.error(f"Error handling key release: {e}")

    def _normalize_key(self, key):
        """Normalize pynput key objects to simple key names"""
        if isinstance(key, pynput_keyboard.KeyCode):
            if key.char:
                return key.char.lower()
            return None

        key_map = {
            pynput_keyboard.Key.ctrl: "ctrl",
            pynput_keyboard.Key.ctrl_l: "ctrl",
            pynput_keyboard.Key.ctrl_r: "ctrl",
            pynput_keyboard.Key.alt: "alt",
            pynput_keyboard.Key.alt_l: "alt",
            pynput_keyboard.Key.alt_r: "alt",
            pynput_keyboard.Key.shift: "shift",
            pynput_keyboard.Key.shift_l: "shift",
            pynput_keyboard.Key.shift_r: "shift",
            pynput_keyboard.Key.cmd: "meta",
            pynput_keyboard.Key.cmd_l: "meta",
            pynput_keyboard.Key.cmd_r: "meta",
            pynput_keyboard.Key.space: "space",
        }
        return key_map.get(key)
    
    def _check_debounce(self) -> bool:
        """Check if enough time has passed since last trigger (debounce)"""
        import time
        current_time = time.time() * 1000  # Convert to milliseconds
        
        if current_time - self.last_trigger_time > self.debounce_ms:
            self.last_trigger_time = current_time
            return True
        
        return False
    
    def set_enabled(self, enabled: bool):
        """Enable or disable hotkey listening"""
        self.enabled = enabled
        self.logger.info(f"Hotkey listener {'enabled' if enabled else 'disabled'}")
