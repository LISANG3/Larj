#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hotkey Listener - Global hotkey monitoring
Monitors mouse buttons and keyboard shortcuts to trigger the panel
"""

import logging
import time
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from pynput import mouse, keyboard as pynput_keyboard

DEFAULT_TRIGGER_KEY = "xbutton1"


def detect_hotkey():
    """
    Blocking hotkey detection (keyboard or mouse), returns normalized string.
    """
    result = None
    event = threading.Event()
    modifiers = set()

    def on_press(key):
        nonlocal result

        if key in (pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r, pynput_keyboard.Key.ctrl):
            modifiers.add("ctrl")
            return
        if key in (pynput_keyboard.Key.alt_l, pynput_keyboard.Key.alt_r, pynput_keyboard.Key.alt):
            modifiers.add("alt")
            return
        if key in (pynput_keyboard.Key.shift_l, pynput_keyboard.Key.shift_r, pynput_keyboard.Key.shift):
            modifiers.add("shift")
            return
        if key in (pynput_keyboard.Key.cmd_l, pynput_keyboard.Key.cmd_r, pynput_keyboard.Key.cmd):
            modifiers.add("meta")
            return

        try:
            key_name = key.char.lower()
        except AttributeError:
            key_name = str(key).replace("Key.", "").lower()

        modifier_order = ["ctrl", "alt", "shift", "meta"]
        ordered_modifiers = [name for name in modifier_order if name in modifiers]
        result = "+".join(ordered_modifiers + [key_name]) if ordered_modifiers else key_name
        event.set()
        return False

    def on_click(x, y, button, pressed):
        nonlocal result
        if pressed:
            button_name = button.name if hasattr(button, "name") else str(button)
            button_map = {
                "left": "mouse_left",
                "right": "mouse_right",
                "middle": "mouse_middle",
                "x1": "xbutton1",
                "x2": "xbutton2",
            }
            normalized = str(button_name).lower()
            result = button_map.get(normalized, normalized)
            event.set()
            return False

    k_listener = pynput_keyboard.Listener(on_press=on_press)
    m_listener = mouse.Listener(on_click=on_click)
    k_listener.start()
    m_listener.start()
    try:
        event.wait()
    finally:
        k_listener.stop()
        m_listener.stop()
    return result


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
        self._normalized_fallback_set = set()
        self._trigger_requires_modifiers = False
        
        # Load configuration
        self.reload_config()
        
        self.logger.info("HotkeyListener initialized")
    
    def reload_config(self):
        """Reload configuration"""
        try:
            self.trigger_key = self._normalize_hotkey(self.config_manager.get("hotkey.trigger_key", DEFAULT_TRIGGER_KEY))
            self.fallback_keys = [
                normalized for normalized in
                (self._normalize_hotkey(k) for k in self.config_manager.get("hotkey.fallback_keys", ["Ctrl+Space"]))
                if normalized != self.trigger_key
            ]
            self._normalized_fallback_set = set(self.fallback_keys)
            self._trigger_requires_modifiers = "+" in self.trigger_key
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
            button_name = button.name if hasattr(button, 'name') else str(button)
            if self._normalize_mouse_button(button_name) != self.trigger_key:
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

            # Fast path: most non-modifier keys can skip subset checks
            # when trigger/fallback are combination shortcuts.
            if (
                not self._trigger_requires_modifiers
                and self.trigger_key == key_name
                and self._check_debounce()
            ):
                self.logger.debug(f"Keyboard trigger {self.trigger_key} triggered")
                self.hotkey_triggered.emit()
                return

            if self._is_shortcut_triggered(self.trigger_key):
                if self._check_debounce():
                    self.logger.debug(f"Keyboard trigger {self.trigger_key} triggered")
                    self.hotkey_triggered.emit()
                return

            for shortcut in self._normalized_fallback_set:
                if not self._is_shortcut_triggered(shortcut):
                    continue
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
        mapped_key = key_map.get(key)
        if mapped_key:
            return mapped_key

        key_str = str(key)
        if key_str.startswith("Key."):
            return key_str.replace("Key.", "").lower()
        return None

    def _normalize_hotkey(self, hotkey):
        """Normalize configured hotkey string"""
        return str(hotkey).strip().lower()

    def _normalize_mouse_button(self, button_name: str) -> str:
        button_map = {
            "x1": "xbutton1",
            "x2": "xbutton2",
            "left": "mouse_left",
            "right": "mouse_right",
            "middle": "mouse_middle",
        }
        normalized = str(button_name).strip().lower()
        return button_map.get(normalized, normalized)

    def _is_shortcut_triggered(self, shortcut: str) -> bool:
        normalized = self._normalize_hotkey(shortcut)
        required_keys = {part.strip() for part in normalized.split('+') if part.strip()}
        return bool(required_keys) and required_keys.issubset(self.pressed_keys)
    
    def _check_debounce(self) -> bool:
        """Check if enough time has passed since last trigger (debounce)"""
        current_time = time.time() * 1000  # Convert to milliseconds
        
        if current_time - self.last_trigger_time > self.debounce_ms:
            self.last_trigger_time = current_time
            return True
        
        return False
    
    def set_enabled(self, enabled: bool):
        """Enable or disable hotkey listening"""
        self.enabled = enabled
        self.logger.info(f"Hotkey listener {'enabled' if enabled else 'disabled'}")
