#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application Manager - Manages quick launch applications
Handles app CRUD operations, launching, and usage tracking
"""

import os
import logging
import shlex
import subprocess
import uuid
import psutil
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal


class ApplicationManager(QObject):
    """
    Application manager - manages application shortcuts
    """
    
    # Signals
    app_launched = pyqtSignal(str)  # app_id
    app_added = pyqtSignal(dict)  # app_data
    app_removed = pyqtSignal(str)  # app_id
    app_updated = pyqtSignal(str, dict)  # app_id, app_data
    
    def __init__(self, config_manager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self._apps_cache = None
        
        # Load configuration
        self.reload_config()
        
        self.logger.info("ApplicationManager initialized")
    
    def reload_config(self):
        """Reload configuration"""
        try:
            self.auto_sort = self.config_manager.get("application.auto_sort", False)
            self.sort_by = self.config_manager.get("application.sort_by", "manual")
            
            self.logger.info(f"App config reloaded: auto_sort={self.auto_sort}, sort_by={self.sort_by}")
            
        except Exception as e:
            self.logger.error(f"Failed to reload app config: {e}")
    
    def get_apps(self) -> List[Dict]:
        """Get all applications"""
        apps = self.config_manager.get_apps()
        self._apps_cache = apps
        
        # Sort if enabled
        if self.auto_sort:
            apps = self._sort_apps(apps)
        
        return apps
    
    def _sort_apps(self, apps: List[Dict]) -> List[Dict]:
        """Sort applications based on configuration"""
        try:
            if self.sort_by in {"manual", "usage"}:
                return apps
            elif self.sort_by == "name":
                # Sort by name (ascending)
                return sorted(apps, key=lambda x: x.get("name", "").lower())
            elif self.sort_by == "date":
                # Sort by creation date (descending)
                return sorted(apps, key=lambda x: x.get("created_at", ""), reverse=True)
            else:
                return apps
                
        except Exception as e:
            self.logger.error(f"Failed to sort apps: {e}")
            return apps
    
    def add_app(self, name: str, path: str, icon_path: str = "", args: str = "") -> Dict:
        """Add new application"""
        try:
            # Validate path
            if not Path(path).exists():
                raise FileNotFoundError(f"Application path not found: {path}")
            
            # Create app data
            app_data = {
                "id": str(uuid.uuid4()),
                "name": name,
                "path": path,
                "icon_path": icon_path,
                "args": args,
                "prefer_activate_existing": False,
                "usage_count": 0,
                "created_at": datetime.now().isoformat(),
                "last_used": None
            }
            
            # Add to config
            self.config_manager.add_app(app_data)
            self._apps_cache = None
            
            # Emit signal
            self.app_added.emit(app_data)
            
            self.logger.info(f"Added app: {name}")
            return app_data
            
        except Exception as e:
            self.logger.error(f"Failed to add app: {e}", exc_info=True)
            raise

    def add_folder(self, folder_path: str) -> Dict:
        """Add a folder shortcut as an app entry."""
        try:
            path_obj = Path(folder_path)
            if not path_obj.exists() or not path_obj.is_dir():
                raise FileNotFoundError(f"Folder path not found: {folder_path}")

            app_data = {
                "id": str(uuid.uuid4()),
                "name": path_obj.name,
                "path": str(path_obj),
                "icon_path": "",
                "args": "",
                "is_folder": True,
                "prefer_activate_existing": False,
                "usage_count": 0,
                "created_at": datetime.now().isoformat(),
                "last_used": None,
            }
            self.config_manager.add_app(app_data)
            self._apps_cache = None
            self.app_added.emit(app_data)
            self.logger.info(f"Added folder: {app_data['name']}")
            return app_data
        except Exception as e:
            self.logger.error(f"Failed to add folder: {e}", exc_info=True)
            raise
    
    def remove_app(self, app_id: str):
        """Remove application"""
        try:
            self.config_manager.remove_app(app_id)
            self._apps_cache = None
            self.app_removed.emit(app_id)
            self.logger.info(f"Removed app: {app_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to remove app: {e}")
    
    def update_app(self, app_id: str, app_data: Dict):
        """Update application data"""
        try:
            self.config_manager.update_app(app_id, app_data)
            self._apps_cache = None
            self.app_updated.emit(app_id, app_data)
            self.logger.info(f"Updated app: {app_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update app: {e}")

    def move_app(self, app_id: str, direction: int) -> bool:
        """Move an app by direction (-1 up, +1 down) and persist order."""
        try:
            apps = self.config_manager.get_apps()
            current_index = next((i for i, app in enumerate(apps) if app.get("id") == app_id), -1)
            if current_index < 0:
                return False

            new_index = current_index + direction
            if new_index < 0 or new_index >= len(apps):
                return False

            apps[current_index], apps[new_index] = apps[new_index], apps[current_index]
            self.config_manager.save_apps()
            self._apps_cache = None
            self.logger.info(f"Moved app: {app_id}, direction={direction}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to move app: {e}", exc_info=True)
            return False
    
    def launch_app(self, app_info: Dict):
        """Launch application or open folder"""
        try:
            app_id = app_info.get("id")
            path = app_info.get("path")
            args = app_info.get("args", "")
            is_folder = app_info.get("is_folder", False)
            prefer_activate_existing = bool(app_info.get("prefer_activate_existing", False))

            if not path:
                raise ValueError("Path is empty")

            path_obj = Path(path)
            if not path_obj.exists():
                raise FileNotFoundError(f"Path not found: {path}")

            if is_folder or path_obj.is_dir():
                if os.name == 'nt':
                    os.startfile(str(path_obj))
                else:
                    subprocess.Popen(['xdg-open', str(path_obj)])
            else:
                activated_existing = False
                if os.name == 'nt' and prefer_activate_existing:
                    activated_existing = self._try_activate_existing_window(path_obj)

                if not activated_existing:
                    if os.name == 'nt':
                        launch_args = args.strip() if isinstance(args, str) and args.strip() else None
                        try:
                            os.startfile(str(path_obj), arguments=launch_args)
                        except TypeError:
                            cmd = [str(path_obj)] + self._split_launch_args(args)
                            subprocess.Popen(cmd, shell=False)
                    else:
                        cmd = [str(path_obj)] + self._split_launch_args(args)
                        subprocess.Popen(cmd, shell=False)
                else:
                    self.logger.info(f"Activated existing window for {path_obj.name}")
            
            self._update_usage_stats(app_id)
            self.app_launched.emit(app_id)
            
            self.logger.info(f"Launched: {app_info.get('name')}")
            
        except Exception as e:
            self.logger.error(f"Failed to launch: {e}", exc_info=True)
            raise

    @staticmethod
    def _split_launch_args(args: str) -> List[str]:
        if not args or not isinstance(args, str) or not args.strip():
            return []
        try:
            return shlex.split(args, posix=True)
        except ValueError as e:
            raise ValueError(f"Invalid launch arguments: {args}") from e

    def _try_activate_existing_window(self, path_obj: Path) -> bool:
        """Try to bring an already running app window to foreground on Windows."""
        if os.name != 'nt':
            return False

        target_exe_name = path_obj.name.lower()
        if not target_exe_name:
            return False

        try:
            import win32con
            import win32gui
            import win32process
        except ImportError as e:
            self.logger.warning(f"Cannot activate existing window without pywin32: {e}")
            return False

        matched = False

        def _enum_windows(hwnd, _):
            nonlocal matched
            if matched or not win32gui.IsWindowVisible(hwnd):
                return

            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
            except win32gui.error:
                return
            if pid <= 0:
                return

            try:
                proc = psutil.Process(pid)
                exe_name = Path(proc.exe()).name.lower()
            except (psutil.Error, OSError, ValueError):
                return

            if exe_name != target_exe_name:
                return

            try:
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                else:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
                matched = True
            except win32gui.error as e:
                self.logger.warning(f"Failed to focus window handle {hwnd} for {target_exe_name}: {e}")

        try:
            win32gui.EnumWindows(_enum_windows, None)
        except win32gui.error as e:
            self.logger.warning(f"Failed while enumerating windows for {target_exe_name}: {e}")
            return False

        return matched
    
    def _update_usage_stats(self, app_id: str):
        """Update application usage statistics"""
        try:
            if self._apps_cache is None:
                self._apps_cache = self.config_manager.get_apps()
            apps = self._apps_cache
            app_updated = False
            
            for app in apps:
                if app.get("id") == app_id:
                    app["usage_count"] = app.get("usage_count", 0) + 1
                    app["last_used"] = datetime.now().isoformat()
                    app_updated = True
                    break
            
            if app_updated:
                self.config_manager.save_apps()
                self.logger.debug(f"Updated usage stats for app: {app_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update usage stats: {e}")
    
    def import_from_start_menu(self):
        """Import applications from Windows Start Menu"""
        # TODO: Implement start menu scanning
        # This would scan common locations like:
        # - %APPDATA%\Microsoft\Windows\Start Menu\Programs
        # - %PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs
        pass
    
    def import_from_desktop(self):
        """Import applications from Desktop"""
        # TODO: Implement desktop scanning
        pass
