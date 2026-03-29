#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for cold-search based SearchEngine module.
"""

import os
import sys
import time
import heapq
from collections import OrderedDict
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

import src.core.search_engine as search_engine_module
from src.core.search_engine import SearchEngine, SearchWorker


@pytest.fixture
def mock_config_manager():
    config = MagicMock()
    defaults = {
        "search.max_results": 50,
        "search.debounce_ms": 300,
        "search.cache_timeout": 60,
        "search.cache_max_size": 40,
        "search.sdk_dll_path": "",
        "search.everything_exe_path": "everything/Everything.exe",
    }
    config.get.side_effect = lambda key, default=None: defaults.get(key, default)
    return config


@pytest.fixture
def search_engine(mock_config_manager):
    engine = SearchEngine(mock_config_manager)
    return engine


class TestSearchCache:
    def test_cache_is_ordered_dict(self, search_engine):
        assert isinstance(search_engine.search_cache, OrderedDict)

    def test_cache_max_size_default(self, search_engine):
        assert search_engine.cache_max_size == 40

    def test_cache_bounded_by_max_size(self, search_engine):
        search_engine.cache_max_size = 5

        for i in range(10):
            keyword = f"search_{i}"
            search_engine._on_search_completed(keyword, [{"name": f"result_{i}"}])

        assert len(search_engine.search_cache) == 5
        assert "search_0" not in search_engine.search_cache
        assert "search_4" not in search_engine.search_cache
        assert "search_9" in search_engine.search_cache
        assert "search_5" in search_engine.search_cache

    def test_clear_cache(self, search_engine):
        search_engine._on_search_completed("test1", [{"name": "r1"}])
        search_engine._on_search_completed("test2", [{"name": "r2"}])
        assert len(search_engine.search_cache) == 2
        search_engine.clear_cache()
        assert len(search_engine.search_cache) == 0

    def test_cache_check_returns_valid(self, search_engine):
        search_engine.search_cache["hello"] = (time.time(), [r"C:\tmp\world.txt"])
        assert search_engine._check_cache("hello") is True

    def test_cache_payload_stores_open_paths_only(self, search_engine):
        payload = search_engine._cache_payload_from_results([
            {"name": "a", "open_path": r"C:\a\a.txt"},
            {"name": "b", "open_path": r"C:\a\b.txt"},
            {"name": "dup", "open_path": r"C:\a\a.txt"},
            {"name": "missing"},
        ])
        assert payload == [r"C:\a\a.txt", r"C:\a\b.txt"]

    def test_restore_cached_paths_rebuilds_ui_shape(self, search_engine):
        restored = search_engine._restore_cached_results([r"C:\x\alpha.txt"])
        assert len(restored) == 1
        assert restored[0]["open_path"] == r"C:\x\alpha.txt"

    def test_cache_check_expired(self, search_engine):
        search_engine.cache_timeout = 0
        search_engine.search_cache["old"] = (time.time() - 1, [])
        assert search_engine._check_cache("old") is False
        assert "old" not in search_engine.search_cache

    def test_cache_check_missing(self, search_engine):
        assert search_engine._check_cache("nonexistent") is False

    def test_cache_hit_refreshes_recency_for_lru_behavior(self, search_engine):
        search_engine.cache_max_size = 2
        search_engine._on_search_completed("first", [{"name": "a"}])
        search_engine._on_search_completed("second", [{"name": "b"}])
        assert search_engine._check_cache("first") is True
        search_engine._on_search_completed("third", [{"name": "c"}])
        assert "first" in search_engine.search_cache
        assert "third" in search_engine.search_cache
        assert "second" not in search_engine.search_cache

    def test_on_search_completed_ignores_stale_token(self, search_engine):
        search_engine._active_search_token = 2
        search_engine._on_search_completed("stale", [{"name": "x"}], token=1)
        assert "stale" not in search_engine.search_cache


class TestColdSearchRanking:
    def test_optimize_results_dedupes_and_prioritizes_name_match(self):
        candidates = [
            (r"C:\a\hello.txt", "hello.txt", r"C:\a"),
            (r"C:\a\hello.txt", "hello.txt", r"C:\a"),
            (r"C:\b\my-hello-note.txt", "my-hello-note.txt", r"C:\b"),
            (r"C:\c\abc.txt", "abc.txt", r"C:\c\hello"),
        ]
        optimized = SearchWorker._optimize_results("hello", candidates, limit=3)
        assert len(optimized) == 3
        assert optimized[0] == r"C:\a\hello.txt"
        assert optimized.count(r"C:\a\hello.txt") == 1

    def test_score_result_prefers_exact_then_prefix(self):
        keyword = "test"
        tokens = ["test"]
        exact = SearchWorker._score_result(keyword, tokens, "test.exe", r"C:\apps")
        partial = SearchWorker._score_result(keyword, tokens, "my-test-tool.exe", r"C:\apps")
        assert exact > partial

    def test_optimize_results_accepts_generator(self):
        def candidates():
            yield (r"C:\a\hello.txt", "hello.txt", r"C:\a")
            yield (r"C:\a\world.txt", "world.txt", r"C:\a")

        optimized = SearchWorker._optimize_results("hello", candidates(), limit=1)
        assert optimized == [r"C:\a\hello.txt"]

    def test_optimize_results_uses_heap_for_topk(self, monkeypatch):
        calls = {"push": 0, "replace": 0}
        real_push = heapq.heappush
        real_replace = heapq.heapreplace

        def wrapped_push(heap, item):
            calls["push"] += 1
            return real_push(heap, item)

        def wrapped_replace(heap, item):
            calls["replace"] += 1
            return real_replace(heap, item)

        monkeypatch.setattr(heapq, "heappush", wrapped_push)
        monkeypatch.setattr(heapq, "heapreplace", wrapped_replace)

        candidates = (
            (fr"C:\a\hello-{i}.txt", f"hello-{i}.txt", r"C:\a")
            for i in range(60)
        )
        optimized = SearchWorker._optimize_results("hello", candidates, limit=10)
        assert len(optimized) == 10
        assert calls["push"] > 0


class TestResultShape:
    def test_to_ui_result_has_required_fields(self):
        full_path = r"C:\Temp\alpha.txt"
        result = SearchWorker._to_ui_result(full_path)
        assert result["name"] == "alpha.txt"
        assert result["path"] == r"C:\Temp"
        assert result["dir_path"] == r"C:\Temp"
        assert result["open_path"] == full_path
        assert result["type"] == "txt"

    def test_to_ui_results_filters_empty_values(self):
        results = SearchWorker._to_ui_results([r"C:\a\b.txt", "", r"C:\c\d.exe"])
        assert len(results) == 2


class TestCleanupStrategy:
    def test_stop_all_everything_processes_stops_until_empty(self, monkeypatch):
        process_state = {"pids": [101, 102]}

        def fake_list():
            return [{"pid": pid, "session": "Console"} for pid in process_state["pids"]]

        def fake_stop(pid):
            process_state["pids"] = [x for x in process_state["pids"] if x != pid]
            return True, ""

        monkeypatch.setattr(SearchWorker, "_list_everything_processes", staticmethod(fake_list))
        monkeypatch.setattr(SearchWorker, "_stop_pid_force", staticmethod(fake_stop))
        monkeypatch.setattr(search_engine_module.time, "sleep", lambda *_: None)

        remaining, failures = SearchWorker._stop_all_everything_processes()
        assert remaining == []
        assert failures == []

    def test_stop_all_everything_processes_reports_failure(self, monkeypatch):
        def fake_list():
            return [{"pid": 201, "session": "Console"}]

        def fake_stop(_pid):
            return False, "denied"

        monkeypatch.setattr(SearchWorker, "_list_everything_processes", staticmethod(fake_list))
        monkeypatch.setattr(SearchWorker, "_stop_pid_force", staticmethod(fake_stop))
        monkeypatch.setattr(search_engine_module.time, "sleep", lambda *_: None)

        remaining, failures = SearchWorker._stop_all_everything_processes()
        assert remaining == [{"pid": 201, "session": "Console"}]
        assert failures == [{"pid": 201, "error": "denied"}]
