#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for SearchEngine cache management
"""

import os
import sys
import time
from collections import OrderedDict
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from src.core.search_engine import SearchEngine


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager"""
    config = MagicMock()
    defaults = {
        "search.es_path": "",
        "search.max_results": 50,
        "search.debounce_ms": 300,
        "search.cache_timeout": 60,
    }
    config.get.side_effect = lambda key, default=None: defaults.get(key, default)
    return config


@pytest.fixture
def search_engine(mock_config_manager):
    """Create a SearchEngine instance with mocked config"""
    engine = SearchEngine(mock_config_manager)
    return engine


class TestSearchCache:
    """Tests for search cache management"""

    def test_cache_is_ordered_dict(self, search_engine):
        assert isinstance(search_engine.search_cache, OrderedDict)

    def test_cache_max_size_default(self, search_engine):
        assert search_engine.cache_max_size == 100

    def test_cache_bounded_by_max_size(self, search_engine):
        search_engine.cache_max_size = 5

        for i in range(10):
            keyword = f"search_{i}"
            search_engine._on_search_completed(keyword, [{"name": f"result_{i}"}])

        assert len(search_engine.search_cache) == 5
        # Oldest entries should have been evicted
        assert "search_0" not in search_engine.search_cache
        assert "search_4" not in search_engine.search_cache
        # Newest entries should remain
        assert "search_9" in search_engine.search_cache
        assert "search_5" in search_engine.search_cache

    def test_cache_evicts_oldest_first(self, search_engine):
        search_engine.cache_max_size = 3

        search_engine._on_search_completed("first", [])
        search_engine._on_search_completed("second", [])
        search_engine._on_search_completed("third", [])
        search_engine._on_search_completed("fourth", [])

        assert "first" not in search_engine.search_cache
        assert "second" in search_engine.search_cache
        assert "third" in search_engine.search_cache
        assert "fourth" in search_engine.search_cache

    def test_clear_cache(self, search_engine):
        search_engine._on_search_completed("test1", [{"name": "r1"}])
        search_engine._on_search_completed("test2", [{"name": "r2"}])
        assert len(search_engine.search_cache) == 2

        search_engine.clear_cache()
        assert len(search_engine.search_cache) == 0

    def test_cache_check_returns_valid(self, search_engine):
        search_engine.search_cache["hello"] = (time.time(), [{"name": "world"}])
        assert search_engine._check_cache("hello") is True

    def test_cache_check_expired(self, search_engine):
        search_engine.cache_timeout = 0
        search_engine.search_cache["old"] = (time.time() - 1, [])
        assert search_engine._check_cache("old") is False
        assert "old" not in search_engine.search_cache

    def test_cache_check_missing(self, search_engine):
        assert search_engine._check_cache("nonexistent") is False
