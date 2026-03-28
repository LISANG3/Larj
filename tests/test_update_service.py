#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for update checking/downloading workflow.
"""

import hashlib
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.update_service import UpdateService, UpdateInfo


@pytest.fixture
def mock_config_manager():
    config = MagicMock()
    defaults = {
        "update.github_owner": "LISANG3",
        "update.github_repo": "Larj",
        "update.request_timeout_sec": 20,
    }
    config.get.side_effect = lambda key, default=None: defaults.get(key, default)
    return config


def test_compare_versions():
    assert UpdateService.compare_versions("0.2.0", "0.1.9") == 1
    assert UpdateService.compare_versions("1.0.0", "1.0.0") == 0
    assert UpdateService.compare_versions("1.0.0", "1.0.1") == -1


def test_extract_sha256_from_text():
    text = "4a44dc15364204a80fe80e9039455cc1608281820fe2b24f6f7e9c9f2a8d2f5a  Larj_v0.2.0.zip"
    got = UpdateService._extract_sha256_from_text(text, "Larj_v0.2.0.zip")
    assert got == "4a44dc15364204a80fe80e9039455cc1608281820fe2b24f6f7e9c9f2a8d2f5a"


def test_check_for_update_parses_release(mock_config_manager):
    service = UpdateService(mock_config_manager)
    service.get_current_version = MagicMock(return_value="0.1.0")

    sample_release = {
        "tag_name": "v0.2.0",
        "name": "v0.2.0",
        "body": "notes",
        "assets": [
            {
                "name": "Larj_v0.2.0.zip",
                "browser_download_url": "https://example.com/Larj_v0.2.0.zip",
            },
            {
                "name": "Larj_v0.2.0.sha256",
                "browser_download_url": "https://example.com/Larj_v0.2.0.sha256",
            },
        ],
    }

    service._request_json = MagicMock(return_value=sample_release)
    service._download_text = MagicMock(
        return_value="4a44dc15364204a80fe80e9039455cc1608281820fe2b24f6f7e9c9f2a8d2f5a  Larj_v0.2.0.zip"
    )

    info = service.check_for_update()
    assert isinstance(info, UpdateInfo)
    assert info.version == "0.2.0"
    assert info.asset_name == "Larj_v0.2.0.zip"
    assert info.sha256 == "4a44dc15364204a80fe80e9039455cc1608281820fe2b24f6f7e9c9f2a8d2f5a"


def test_download_update_verifies_hash(mock_config_manager):
    service = UpdateService(mock_config_manager)
    payload = b"hello-update"
    expected = hashlib.sha256(payload).hexdigest()
    info = UpdateInfo(
        version="0.2.0",
        release_name="v0.2.0",
        release_notes="",
        asset_name="pkg.zip",
        asset_url="http://example.com/pkg.zip",
        sha256=expected,
    )

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=8192):
            yield payload

    import src.core.update_service as update_mod

    old_get = update_mod.requests.get
    update_mod.requests.get = lambda *args, **kwargs: FakeResp()
    try:
        path = service.download_update(info)
        assert path.exists()
        assert path.read_bytes() == payload
    finally:
        update_mod.requests.get = old_get


def test_get_current_version_reads_version_file(mock_config_manager):
    with tempfile.TemporaryDirectory() as td:
        old = os.getcwd()
        try:
            os.chdir(td)
            Path("VERSION").write_text("1.2.3\n", encoding="utf-8")
            service = UpdateService(mock_config_manager)
            assert service.get_current_version() == "1.2.3"
        finally:
            os.chdir(old)


def test_get_current_version_from_executable_name_when_version_missing(mock_config_manager):
    with tempfile.TemporaryDirectory() as td:
        service = UpdateService(mock_config_manager)
        with patch.object(UpdateService, "_resolve_app_dir", return_value=Path(td)), \
                patch.object(sys, "executable", str(Path(td) / "Larj_v1.4.5.exe")):
            assert service.get_current_version() == "1.4.5"


def test_check_for_update_returns_none_when_versions_equal(mock_config_manager):
    service = UpdateService(mock_config_manager)
    service.get_current_version = MagicMock(return_value="1.2.3")
    service._request_json = MagicMock(
        return_value={
            "tag_name": "v1.2.3",
            "name": "v1.2.3",
            "body": "notes",
            "assets": [],
        }
    )
    assert service.check_for_update() is None
