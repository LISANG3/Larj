#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sample Plugin - Notepad
A simple notepad launcher plugin
"""

from src.core.plugin_system import PluginBase


class NotepadPlugin(PluginBase):
    """
    Notepad launcher plugin
    """
    
    def get_name(self) -> str:
        return "Notepad"
    
    def get_icon(self) -> str:
        return "notepad"
    
    def get_info(self) -> dict:
        return {
            "name": "Notepad",
            "version": "1.0.0",
            "author": "Larj Team",
            "description": "Quick access to Notepad"
        }
    
    def handle_click(self):
        """Open Windows Notepad"""
        import subprocess
        import os
        
        if os.name == 'nt':  # Windows
            subprocess.Popen('notepad.exe')
        else:
            print("Notepad plugin is only available on Windows")
    
    def on_load(self):
        """Called when plugin is loaded"""
        print("Notepad plugin loaded")
    
    def on_unload(self):
        """Called when plugin is unloaded"""
        print("Notepad plugin unloaded")
