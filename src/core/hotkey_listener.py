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
                on_press=self._on_key_press
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
            if button_name in ['x1', 'x2'] or 'XButton' in self.trigger_key:
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
            # Check fallback keyboard shortcuts
            # For now, we'll implement a simple Ctrl+Space check
            # TODO: Implement more sophisticated hotkey combination detection
            
            # This is a simplified implementation
            # A full implementation would track modifier keys (Ctrl, Alt, Shift)
            # and detect key combinations
            
            pass  # Placeholder for keyboard shortcut detection
            
        except Exception as e:
            self.logger.error(f"Error handling key press: {e}")
    
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
