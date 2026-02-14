#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sample Plugin - Calculator
A simple calculator plugin for demonstration
"""

from src.core.plugin_system import PluginBase


class CalculatorPlugin(PluginBase):
    """
    Simple calculator plugin
    """
    
    def get_name(self) -> str:
        return "Calculator"
    
    def get_icon(self) -> str:
        return "calculator"
    
    def get_info(self) -> dict:
        return {
            "name": "Calculator",
            "version": "1.0.0",
            "author": "Larj Team",
            "description": "A simple calculator plugin"
        }
    
    def handle_click(self):
        """Open Windows calculator"""
        import subprocess
        import os
        
        if os.name == 'nt':  # Windows
            subprocess.Popen('calc.exe')
        else:
            print("Calculator plugin is only available on Windows")
    
    def on_load(self):
        """Called when plugin is loaded"""
        print("Calculator plugin loaded")
    
    def on_unload(self):
        """Called when plugin is unloaded"""
        print("Calculator plugin unloaded")
