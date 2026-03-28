#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search Engine - cold-search pipeline based on Everything SDK.
"""

import ctypes
import csv
import logging
import struct
import subprocess
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSignal


class EverythingSDKError(RuntimeError):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


class EverythingSDKClient:
    EVERYTHING_ERROR_IPC = 2
    EVERYTHING_SORT_NAME_ASCENDING = 1
    EVERYTHING_REQUEST_FILE_NAME = 0x00000001
    EVERYTHING_REQUEST_PATH = 0x00000002

    ERROR_MESSAGES = {
        0: "OK",
        1: "Memory allocation failed",
        2: "IPC unavailable",
        3: "RegisterClassEx failed",
        4: "CreateWindow failed",
        5: "CreateThread failed",
        6: "Invalid index",
        7: "Invalid call",
    }

    def __init__(self, configured_dll_path: str = ""):
        self.dll_path = self._resolve_dll_path(configured_dll_path)
        self.dll = self._load_dll(self.dll_path)
        self._bind_functions()

    @staticmethod
    def _platform_dll_names() -> List[str]:
        is_64bit = struct.calcsize("P") * 8 == 64
        if is_64bit:
            return ["Everything64.dll", "Everything.dll"]
        return ["Everything32.dll", "Everything.dll"]

    @classmethod
    def _resolve_dll_path(cls, configured_dll_path: str) -> str:
        if configured_dll_path:
            candidate = Path(configured_dll_path).expanduser()
            if not candidate.is_absolute():
                candidate = (Path.cwd() / candidate).resolve()
            if candidate.exists():
                return str(candidate)

        everything_dir = Path.cwd() / "everything"
        for dll_name in cls._platform_dll_names():
            candidates = [
                everything_dir / dll_name,
                everything_dir / "dll" / dll_name,
            ]
            for candidate in candidates:
                if candidate.exists():
                    return str(candidate.resolve())
        return cls._platform_dll_names()[0]

    @staticmethod
    def _load_dll(dll_path: str):
        try:
            return ctypes.WinDLL(dll_path, use_last_error=True)
        except OSError as e:
            raise RuntimeError(f"Failed to load Everything SDK DLL: {dll_path} ({e})") from e

    def _bind_functions(self):
        d = self.dll
        d.Everything_SetSearchW.argtypes = [ctypes.c_wchar_p]
        d.Everything_SetSearchW.restype = None
        d.Everything_SetMatchPath.argtypes = [ctypes.c_bool]
        d.Everything_SetMatchPath.restype = None
        d.Everything_SetMatchCase.argtypes = [ctypes.c_bool]
        d.Everything_SetMatchCase.restype = None
        d.Everything_SetMatchWholeWord.argtypes = [ctypes.c_bool]
        d.Everything_SetMatchWholeWord.restype = None
        d.Everything_SetRegex.argtypes = [ctypes.c_bool]
        d.Everything_SetRegex.restype = None
        d.Everything_SetSort.argtypes = [ctypes.c_uint32]
        d.Everything_SetSort.restype = None
        d.Everything_SetRequestFlags.argtypes = [ctypes.c_uint32]
        d.Everything_SetRequestFlags.restype = None
        d.Everything_SetMax.argtypes = [ctypes.c_uint32]
        d.Everything_SetMax.restype = None
        d.Everything_SetOffset.argtypes = [ctypes.c_uint32]
        d.Everything_SetOffset.restype = None
        d.Everything_QueryW.argtypes = [ctypes.c_bool]
        d.Everything_QueryW.restype = ctypes.c_bool
        d.Everything_GetNumResults.argtypes = []
        d.Everything_GetNumResults.restype = ctypes.c_uint32
        d.Everything_GetResultFileNameW.argtypes = [ctypes.c_uint32]
        d.Everything_GetResultFileNameW.restype = ctypes.c_wchar_p
        d.Everything_GetResultPathW.argtypes = [ctypes.c_uint32]
        d.Everything_GetResultPathW.restype = ctypes.c_wchar_p
        d.Everything_GetLastError.argtypes = []
        d.Everything_GetLastError.restype = ctypes.c_uint32
        d.Everything_Reset.argtypes = []
        d.Everything_Reset.restype = None

    def is_ipc_ready(self) -> bool:
        d = self.dll
        d.Everything_SetSearchW("")
        d.Everything_SetRequestFlags(self.EVERYTHING_REQUEST_FILE_NAME)
        d.Everything_SetMax(1)
        if d.Everything_QueryW(False):
            return True
        return int(d.Everything_GetLastError()) != self.EVERYTHING_ERROR_IPC

    def fetch_candidates(
        self,
        keyword: str,
        page_size: int,
        max_candidates: int,
        match_path: bool = False,
    ) -> Iterator[Tuple[str, str, str]]:
        d = self.dll
        d.Everything_SetSearchW(keyword)
        d.Everything_SetMatchPath(bool(match_path))
        d.Everything_SetMatchCase(False)
        d.Everything_SetMatchWholeWord(False)
        d.Everything_SetRegex(False)
        d.Everything_SetSort(self.EVERYTHING_SORT_NAME_ASCENDING)
        d.Everything_SetRequestFlags(self.EVERYTHING_REQUEST_FILE_NAME | self.EVERYTHING_REQUEST_PATH)

        offset = 0
        produced = 0
        size = max(1, int(page_size))
        limit = max(1, int(max_candidates))

        try:
            while produced < limit:
                current_max = min(size, limit - produced)
                d.Everything_SetOffset(offset)
                d.Everything_SetMax(current_max)
                ok = bool(d.Everything_QueryW(True))
                if not ok:
                    code = int(d.Everything_GetLastError())
                    reason = self.ERROR_MESSAGES.get(code, f"Unknown error: {code}")
                    raise EverythingSDKError(code, f"Everything query failed: {reason}")

                count = int(d.Everything_GetNumResults())
                if count <= 0:
                    break

                for idx in range(count):
                    name = d.Everything_GetResultFileNameW(idx) or ""
                    path = d.Everything_GetResultPathW(idx) or ""
                    full_path = f"{path}\\{name}" if path else name
                    if not full_path:
                        continue
                    yield full_path, name, path
                    produced += 1
                    if produced >= limit:
                        break

                offset += count
                if count < current_max:
                    break
        finally:
            d.Everything_Reset()


class SearchWorker(QThread):
    search_completed = pyqtSignal(list)
    search_failed = pyqtSignal(str)

    PAGE_SIZE = 2048
    MAX_CANDIDATES = 3000
    READY_TIMEOUT_SEC = 10.0
    READY_POLL_SEC = 0.08
    STOP_WAIT_SEC = 0.5
    _everything_lock = threading.Lock()

    def __init__(
        self,
        sdk_client: EverythingSDKClient,
        keyword: str,
        max_results: int,
        everything_exe_path: str,
    ):
        super().__init__()
        self.sdk_client = sdk_client
        self.keyword = (keyword or "").strip()
        self.max_results = max(1, int(max_results))
        self.everything_exe_path = everything_exe_path
        self.logger = logging.getLogger(__name__)

    def run(self):
        startup_proc = None
        interrupted = False
        try:
            if not self.keyword:
                self.search_completed.emit([])
                return

            with SearchWorker._everything_lock:
                self._warn_on_service_session(self._list_everything_processes(), "before cold boot")
                if self.isInterruptionRequested():
                    interrupted = True
                    return
                exe_path = self._resolve_everything_exe_path()
                self._cold_boot_service(exe_path)
                startup_proc = self._start_hidden_startup_client(exe_path)
                self._wait_ipc_ready()
                if self.isInterruptionRequested():
                    interrupted = True
                    return

                candidates = self.sdk_client.fetch_candidates(
                    keyword=self.keyword,
                    page_size=self.PAGE_SIZE,
                    max_candidates=self.MAX_CANDIDATES,
                    match_path=False,
                )
                results = self._optimize_results_to_ui(self.keyword, candidates, self.max_results)
                if not self.isInterruptionRequested():
                    self.search_completed.emit(results)
        except Exception as e:
            if str(e) == "Search interrupted":
                interrupted = True
            else:
                self.logger.error("Search error: %s", e, exc_info=True)
                self.search_failed.emit(str(e))
        finally:
            cleanup_before = self._list_everything_processes()
            with SearchWorker._everything_lock:
                self._stop_process(startup_proc)
                if startup_proc is not None:
                    self._stop_process_tree(startup_proc.pid)
                try:
                    exe_path = self._resolve_everything_exe_path()
                    self._stop_service_stack(exe_path)
                except Exception as e:
                    self.logger.warning("Everything cleanup failed: %s", e)
                remaining, failures = self._stop_all_everything_processes()
                cleanup_after = self._list_everything_processes()
            self.logger.info("Everything cleanup pids before=%s after=%s", cleanup_before, cleanup_after)
            if failures:
                self.logger.warning("Everything force-stop failures: %s", failures)
            if remaining:
                self.logger.warning("Everything residual processes: %s", remaining)
            self._warn_on_service_session(cleanup_after, "after cleanup")
            if interrupted:
                self.logger.debug("Search worker interrupted and cleaned up")

    def _resolve_everything_exe_path(self) -> str:
        exe_path = Path(self.everything_exe_path).expanduser()
        if not exe_path.is_absolute():
            exe_path = (Path.cwd() / exe_path).resolve()
        if not exe_path.exists():
            raise FileNotFoundError(f"Everything executable not found: {exe_path}")
        return str(exe_path)

    @staticmethod
    def _run_quiet(args: List[str]):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            args,
            creationflags=creationflags,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    def _cold_boot_service(self, exe_path: str):
        self._run_quiet([exe_path, "-stop-client-service"])
        self._run_quiet([exe_path, "-stop-service"])
        time.sleep(self.STOP_WAIT_SEC)
        self._run_quiet([exe_path, "-start-service"])

    def _stop_service_stack(self, exe_path: str):
        self._run_quiet([exe_path, "-stop-client-service"])
        self._run_quiet([exe_path, "-stop-service"])

    @staticmethod
    def _stop_process_tree(root_pid: int):
        if not root_pid:
            return
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        script = f"""
$root = {int(root_pid)}
$ids = @()
function Add-Children([int]$procId) {{
  $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$procId" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessId
  foreach ($child in $children) {{
    Add-Children $child
    $script:ids += [int]$child
  }}
}}
Add-Children $root
$targets = @($ids + $root) | Sort-Object -Descending -Unique
foreach ($id in $targets) {{
  Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
}}
"""
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            creationflags=creationflags,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=4.0,
        )

    @staticmethod
    def _list_everything_processes() -> List[Dict]:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Everything.exe", "/FO", "CSV", "/NH"],
            creationflags=creationflags,
            close_fds=True,
            capture_output=True,
            text=True,
            check=False,
        )
        processes = []
        for line in (result.stdout or "").splitlines():
            text = line.strip()
            if not text or text.upper().startswith("INFO:"):
                continue
            try:
                cols = next(csv.reader([text]))
            except Exception:
                continue
            if len(cols) < 3:
                continue
            name = cols[0].strip().strip('"').lower()
            pid_text = cols[1].strip().strip('"').replace(",", "")
            session_name = cols[2].strip().strip('"')
            if name == "everything.exe" and pid_text.isdigit():
                processes.append({"pid": int(pid_text), "session": session_name})
        unique = {}
        for item in processes:
            unique[item["pid"]] = item
        return [unique[pid] for pid in sorted(unique)]

    @staticmethod
    def _stop_pid_force(pid: int) -> Tuple[bool, str]:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        ps = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                (
                    f"try {{ Stop-Process -Id {int(pid)} -Force -ErrorAction Stop; exit 0 }} "
                    "catch { Write-Output $_.Exception.Message; exit 9 }"
                ),
            ],
            creationflags=creationflags,
            close_fds=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=3.0,
        )
        if ps.returncode == 0:
            return True, ""

        tk = subprocess.run(
            ["taskkill", "/PID", str(int(pid)), "/F", "/T"],
            creationflags=creationflags,
            close_fds=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=3.0,
        )
        if tk.returncode == 0:
            return True, ""

        message = " | ".join(
            part.strip()
            for part in [ps.stdout or "", ps.stderr or "", tk.stdout or "", tk.stderr or ""]
            if part and part.strip()
        )
        return False, message or "unknown error"

    @classmethod
    def _stop_all_everything_processes(cls) -> Tuple[List[Dict], List[Dict]]:
        failures: Dict[int, str] = {}
        for _ in range(6):
            processes = cls._list_everything_processes()
            if not processes:
                return [], [{"pid": pid, "error": msg} for pid, msg in sorted(failures.items())]
            for item in processes:
                pid = item["pid"]
                ok, msg = cls._stop_pid_force(pid)
                if not ok:
                    failures[pid] = msg
            time.sleep(0.12)
        remaining = cls._list_everything_processes()
        return remaining, [{"pid": pid, "error": msg} for pid, msg in sorted(failures.items())]

    @staticmethod
    def _start_hidden_startup_client(exe_path: str):
        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return subprocess.Popen(
            [exe_path, "-startup"],
            creationflags=creationflags,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def _stop_process(proc):
        if not proc:
            return
        try:
            proc.terminate()
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass
        except OSError:
            pass

    def _wait_ipc_ready(self):
        deadline = time.monotonic() + self.READY_TIMEOUT_SEC
        while time.monotonic() < deadline:
            if self.isInterruptionRequested():
                raise RuntimeError("Search interrupted")
            if self.sdk_client.is_ipc_ready():
                return
            time.sleep(self.READY_POLL_SEC)
        if not self.sdk_client.is_ipc_ready():
            raise RuntimeError("Everything IPC is not ready after cold boot")

    @staticmethod
    def _score_result(keyword_lc: str, tokens: List[str], name: str, path: str) -> int:
        name_lc = (name or "").lower()
        path_lc = (path or "").lower()
        score = 0
        if name_lc == keyword_lc:
            score += 1000
        if name_lc.startswith(keyword_lc):
            score += 400
        if keyword_lc in name_lc:
            score += 200
        if keyword_lc in path_lc:
            score += 60

        if tokens:
            in_name = sum(1 for token in tokens if token in name_lc)
            in_path = sum(1 for token in tokens if token in path_lc)
            score += in_name * 70 + in_path * 20

        score += max(0, 80 - min(len(name_lc), 80))
        return score

    @staticmethod
    def _is_better_rank(
        left: Tuple[int, int, str, str],
        right: Tuple[int, int, str, str],
    ) -> bool:
        if left[0] != right[0]:
            return left[0] > right[0]
        if left[1] != right[1]:
            return left[1] < right[1]
        return left[2] < right[2]

    @classmethod
    def _is_worse_rank(
        cls,
        left: Tuple[int, int, str, str],
        right: Tuple[int, int, str, str],
    ) -> bool:
        return cls._is_better_rank(right, left)

    @classmethod
    def _optimize_results(
        cls,
        keyword: str,
        candidates: Iterable[Tuple[str, str, str]],
        limit: int,
    ) -> List[str]:
        if limit <= 0:
            return []

        keyword_lc = keyword.lower()
        tokens = [t for t in keyword_lc.replace("\\", " ").replace("/", " ").split() if t]
        top: List[Tuple[int, int, str, str]] = []
        seen = set()

        for full_path, name, path in candidates:
            key = full_path.lower()
            if key in seen:
                continue
            seen.add(key)
            score = cls._score_result(keyword_lc, tokens, name, path)
            item = (score, len(name), key, full_path)

            if len(top) < limit:
                top.append(item)
                continue

            worst_index = 0
            for idx in range(1, len(top)):
                if cls._is_worse_rank(top[idx], top[worst_index]):
                    worst_index = idx

            if cls._is_better_rank(item, top[worst_index]):
                top[worst_index] = item

        ranked = sorted(top, key=lambda item: (-item[0], item[1], item[2]))
        return [item[3] for item in ranked]

    @classmethod
    def _optimize_results_to_ui(
        cls,
        keyword: str,
        candidates: Iterable[Tuple[str, str, str]],
        limit: int,
    ) -> List[Dict]:
        return cls._to_ui_results(cls._optimize_results(keyword, candidates, limit))

    def _warn_on_service_session(self, processes: List[Dict], context: str):
        service_pids = [item["pid"] for item in processes if str(item.get("session", "")).lower() == "services"]
        if service_pids:
            self.logger.warning(
                "Everything runs in service session %s; cleanup may be denied without same privilege",
                {"context": context, "pids": service_pids},
            )

    @staticmethod
    def _to_ui_result(full_path: str) -> Dict:
        path_obj = Path(full_path)
        name = path_obj.name or str(path_obj)
        dir_path = str(path_obj.parent) if path_obj.parent != path_obj else str(path_obj)
        suffix = path_obj.suffix.lower()
        file_type = suffix[1:] if suffix else "folder"
        return {
            "name": name,
            "path": dir_path,
            "dir_path": dir_path,
            "open_path": str(path_obj),
            "size": 0,
            "date_modified": "",
            "type": file_type,
        }

    @classmethod
    def _to_ui_results(cls, full_paths: List[str]) -> List[Dict]:
        return [cls._to_ui_result(item) for item in full_paths if item]


class SearchEngine(QObject):
    search_completed = pyqtSignal(list)
    search_failed = pyqtSignal(str)

    def __init__(self, config_manager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        self.current_worker = None
        self._active_search_token = 0
        self.search_cache = OrderedDict()
        self.cache_max_size = 40
        self.cache_timeout = 60

        self.sdk_dll_path = ""
        self.everything_exe_path = str(Path("everything") / "Everything.exe")
        self.max_results = 50
        self.debounce_ms = 300
        self.sdk_client: Optional[EverythingSDKClient] = None

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._execute_search)
        self.pending_keyword = ""

        self.reload_config()
        self.logger.info("SearchEngine initialized")

    def reload_config(self):
        try:
            self.max_results = self.config_manager.get("search.max_results", 50)
            self.debounce_ms = self.config_manager.get("search.debounce_ms", 300)
            self.cache_timeout = self.config_manager.get("search.cache_timeout", 60)
            self.cache_max_size = max(1, int(self.config_manager.get("search.cache_max_size", self.cache_max_size)))
            self.sdk_dll_path = self.config_manager.get("search.sdk_dll_path", "") or ""
            self.everything_exe_path = self.config_manager.get(
                "search.everything_exe_path",
                str(Path("everything") / "Everything.exe"),
            )
            self.sdk_client = EverythingSDKClient(self.sdk_dll_path)
            self.logger.info(
                "Search config reloaded: max_results=%s debounce=%sms cache_max=%s",
                self.max_results,
                self.debounce_ms,
                self.cache_max_size,
            )
        except Exception as e:
            self.sdk_client = None
            self.logger.error("Failed to reload search config: %s", e, exc_info=True)

    def search(self, keyword: str):
        if not keyword or not keyword.strip():
            self.search_completed.emit([])
            return

        keyword = keyword.strip()
        if self._check_cache(keyword):
            return

        self.pending_keyword = keyword
        self.debounce_timer.stop()
        self.debounce_timer.start(self.debounce_ms)

    def _check_cache(self, keyword: str) -> bool:
        if keyword in self.search_cache:
            timestamp, cached_payload = self.search_cache[keyword]
            if time.time() - timestamp < self.cache_timeout:
                self.search_cache.move_to_end(keyword)
                self.search_completed.emit(self._restore_cached_results(cached_payload))
                return True
            del self.search_cache[keyword]
        return False

    def _execute_search(self):
        keyword = self.pending_keyword
        if not keyword:
            return

        if self.sdk_client is None:
            self.search_failed.emit("Everything SDK unavailable")
            return

        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.requestInterruption()
        self._active_search_token += 1
        active_token = self._active_search_token

        self.current_worker = SearchWorker(
            sdk_client=self.sdk_client,
            keyword=keyword,
            max_results=self.max_results,
            everything_exe_path=self.everything_exe_path,
        )
        self.current_worker.search_completed.connect(
            lambda results, kw=keyword, token=active_token: self._on_search_completed(kw, results, token=token)
        )
        self.current_worker.search_failed.connect(self.search_failed.emit)
        self.current_worker.start()

    def _on_search_completed(self, keyword: str, results: List[Dict], token: int = None):
        if token is not None and token != self._active_search_token:
            return
        self.search_cache[keyword] = (time.time(), self._cache_payload_from_results(results))
        while len(self.search_cache) > self.cache_max_size:
            self.search_cache.popitem(last=False)
        self.search_completed.emit(results)

    @staticmethod
    def _cache_payload_from_results(results: List[Dict]) -> List[str]:
        paths: List[str] = []
        seen = set()
        for item in results or []:
            if not isinstance(item, dict):
                continue
            path = item.get("open_path")
            if path:
                key = str(path).lower()
                if key in seen:
                    continue
                seen.add(key)
                paths.append(str(path))
        return paths

    @staticmethod
    def _restore_cached_results(payload) -> List[Dict]:
        if not isinstance(payload, list):
            return []
        if not payload:
            return []
        if isinstance(payload[0], dict):
            return payload
        return SearchWorker._to_ui_results([str(item) for item in payload if item])

    def cancel_search(self):
        self.debounce_timer.stop()
        self.pending_keyword = ""
        self._active_search_token += 1
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.requestInterruption()

    def clear_cache(self):
        self.search_cache.clear()
