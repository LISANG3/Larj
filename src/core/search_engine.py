#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search Engine - File search using Everything
Integrates with Everything's es.exe for fast file searching
"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import List, Dict
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread


class SearchWorker(QThread):
    """Worker thread for executing search without blocking UI"""
    
    search_completed = pyqtSignal(list)
    search_failed = pyqtSignal(str)
    
    def __init__(self, es_path: str, keyword: str, max_results: int):
        super().__init__()
        self.es_path = es_path
        self.keyword = keyword
        self.max_results = max_results
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Execute search in separate thread"""
        try:
            # Execute search
            result = self._run_search_command()
            if result.returncode != 0 and self._should_retry_with_everything(result):
                if self._start_everything():
                    time.sleep(0.8)
                    result = self._run_search_command()
            
            if result.returncode == 0:
                # Parse JSON output
                try:
                    data = json.loads(result.stdout)
                    results = data.get("results", [])
                    
                    # Transform results to internal format
                    transformed_results = []
                    for item in results:
                        transformed_results.append({
                            "name": item.get("name", ""),
                            "path": item.get("path", ""),
                            "size": item.get("size", 0),
                            "date_modified": item.get("date_modified", ""),
                            "type": self._get_file_type(item.get("name", ""))
                        })
                    
                    self.search_completed.emit(transformed_results)
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse search results: {e}")
                    self.search_failed.emit(f"Failed to parse results: {e}")
            else:
                self.search_failed.emit(f"Search failed with code {result.returncode}")
                
        except subprocess.TimeoutExpired:
            self.search_failed.emit("Search timeout")
        except Exception as e:
            self.logger.error(f"Search error: {e}", exc_info=True)
            self.search_failed.emit(str(e))

    def _run_search_command(self):
        """Run es.exe search command"""
        cmd = [
            self.es_path,
            "-n", str(self.max_results),  # Limit results
            "-json",  # Output as JSON
            self.keyword
        ]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8'
        )

    def _should_retry_with_everything(self, result) -> bool:
        """Retry once after starting Everything when connection is unavailable"""
        if os.name != "nt":
            return False
        output = f"{result.stdout}\n{result.stderr}".lower()
        markers = ["ipc", "not running", "failed to connect", "createfilemapping"]
        return any(marker in output for marker in markers)

    def _start_everything(self) -> bool:
        """Try to start Everything main process"""
        everything_exe = Path(self.es_path).with_name("Everything.exe")
        if not everything_exe.exists():
            return False
        try:
            subprocess.Popen(
                [str(everything_exe), "-startup"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            return True
        except Exception as e:
            self.logger.warning(f"Failed to auto-start Everything: {e}")
            return False
    
    def _get_file_type(self, filename: str) -> str:
        """Get file type from filename"""
        ext = Path(filename).suffix.lower()
        if ext:
            return ext[1:]  # Remove dot
        return "unknown"


class SearchEngine(QObject):
    """
    Search engine - manages file search using Everything
    """
    
    # Signals
    search_completed = pyqtSignal(list)  # results
    search_failed = pyqtSignal(str)  # error message
    
    def __init__(self, config_manager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        
        # Everything executable path
        project_root = Path(__file__).resolve().parents[2]
        configured_es_path = self.config_manager.get("search.es_path", "")
        if configured_es_path:
            es_path = Path(configured_es_path).expanduser()
            self.es_path = es_path if es_path.is_absolute() else (project_root / es_path).resolve()
        else:
            self.es_path = (project_root / "everything" / "es.exe").resolve()
        
        # Search state
        self.current_worker = None
        self.search_cache = {}  # keyword -> (timestamp, results)
        self.cache_timeout = 60  # seconds
        
        # Debounce timer for real-time search
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._execute_search)
        self.pending_keyword = ""
        
        # Load configuration
        self.reload_config()
        
        self.logger.info("SearchEngine initialized")
        
        # Verify Everything is available
        if not self.es_path.exists():
            self.logger.warning(f"Everything es.exe not found at {self.es_path}")
            self.logger.warning("File search will not be available. Please place es.exe in everything/ directory")
    
    def reload_config(self):
        """Reload configuration"""
        try:
            self.max_results = self.config_manager.get("search.max_results", 50)
            self.debounce_ms = self.config_manager.get("search.debounce_ms", 300)
            self.cache_timeout = self.config_manager.get("search.cache_timeout", 60)
            
            self.logger.info(f"Search config reloaded: max_results={self.max_results}, debounce={self.debounce_ms}ms")
            
        except Exception as e:
            self.logger.error(f"Failed to reload search config: {e}")
    
    def search(self, keyword: str):
        """
        Initiate search with debouncing
        This is called when user types in search box
        """
        if not keyword or not keyword.strip():
            self.search_completed.emit([])
            return
        
        keyword = keyword.strip()
        
        # Check cache first
        if self._check_cache(keyword):
            return
        
        # Set pending keyword and restart debounce timer
        self.pending_keyword = keyword
        self.debounce_timer.stop()
        self.debounce_timer.start(self.debounce_ms)
        
        self.logger.debug(f"Search requested: {keyword}")
    
    def _check_cache(self, keyword: str) -> bool:
        """Check if keyword exists in cache and is still valid"""
        if keyword in self.search_cache:
            timestamp, results = self.search_cache[keyword]
            if time.time() - timestamp < self.cache_timeout:
                self.logger.debug(f"Using cached results for: {keyword}")
                self.search_completed.emit(results)
                return True
            else:
                # Cache expired
                del self.search_cache[keyword]
        
        return False
    
    def _execute_search(self):
        """Execute the actual search after debounce"""
        keyword = self.pending_keyword
        
        if not keyword:
            return
        
        # Cancel previous search if running
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate()
            self.current_worker.wait()
        
        # Check if es.exe exists
        if not self.es_path.exists():
            self.search_failed.emit("Everything es.exe not found. Please place it in everything/ directory")
            return
        
        # Start new search in worker thread
        self.current_worker = SearchWorker(str(self.es_path), keyword, self.max_results)
        self.current_worker.search_completed.connect(lambda results: self._on_search_completed(keyword, results))
        self.current_worker.search_failed.connect(self.search_failed.emit)
        self.current_worker.start()
        
        self.logger.debug(f"Executing search: {keyword}")
    
    def _on_search_completed(self, keyword: str, results: List[Dict]):
        """Handle search completion"""
        # Update cache
        self.search_cache[keyword] = (time.time(), results)
        
        # Emit results
        self.search_completed.emit(results)
        
        self.logger.debug(f"Search completed: {keyword} ({len(results)} results)")
    
    def cancel_search(self):
        """Cancel current search"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate()
            self.current_worker.wait()
            self.logger.debug("Search cancelled")
