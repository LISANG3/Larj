#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update service for checking/downloading releases from GitHub.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests


@dataclass
class UpdateInfo:
    """Resolved update payload metadata."""

    version: str
    release_name: str
    release_notes: str
    asset_name: str
    asset_url: str
    sha256: str


class UpdateService:
    """Check latest release and download verified update package."""

    def __init__(self, config_manager):
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

    @staticmethod
    def normalize_version(raw: str) -> str:
        value = (raw or "").strip()
        if value.lower().startswith("v"):
            value = value[1:]
        return value

    @classmethod
    def compare_versions(cls, left: str, right: str) -> int:
        """Compare semantic-like versions, return 1/0/-1."""
        l_parts = cls._parse_version_parts(left)
        r_parts = cls._parse_version_parts(right)
        if l_parts > r_parts:
            return 1
        if l_parts < r_parts:
            return -1
        return 0

    @classmethod
    def _parse_version_parts(cls, raw: str) -> tuple[int, int, int]:
        value = cls.normalize_version(raw)
        chunks = value.split(".")
        if len(chunks) != 3:
            raise ValueError(f"Invalid version format: {raw}")
        return int(chunks[0]), int(chunks[1]), int(chunks[2])

    def get_current_version(self) -> str:
        """Read current app version from VERSION file."""
        version_file = Path("VERSION")
        if version_file.exists():
            version = version_file.read_text(encoding="utf-8").strip()
            if version:
                return self.normalize_version(version)
        from src import __version__

        return self.normalize_version(__version__)

    def _github_latest_release_url(self) -> str:
        owner = self.config_manager.get("update.github_owner", "LISANG3")
        repo = self.config_manager.get("update.github_repo", "Larj")
        return f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

    def _request_json(self, url: str) -> dict:
        timeout = self.config_manager.get("update.request_timeout_sec", 20)
        resp = requests.get(
            url,
            headers={"Accept": "application/vnd.github+json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _download_text(self, url: str) -> str:
        timeout = self.config_manager.get("update.request_timeout_sec", 20)
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _pick_manifest_asset(assets: list[dict]) -> Optional[dict]:
        for asset in assets:
            name = str(asset.get("name", "")).lower()
            if name in ("update-manifest.json", "manifest.json"):
                return asset
        return None

    @staticmethod
    def _pick_package_asset(assets: list[dict], preferred_name: Optional[str] = None) -> Optional[dict]:
        if preferred_name:
            for asset in assets:
                if asset.get("name") == preferred_name:
                    return asset
        for ext in (".zip", ".7z", ".exe"):
            for asset in assets:
                if str(asset.get("name", "")).lower().endswith(ext):
                    return asset
        return None

    @staticmethod
    def _extract_sha256_from_text(text: str, target_name: str) -> Optional[str]:
        target = target_name.strip().lower()
        hex64_pattern = re.compile(r"\b[a-fA-F0-9]{64}\b")
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lower_line = line.lower()
            if target and target in lower_line:
                parts = line.split()
                if parts:
                    candidate = parts[0].strip()
                    if len(candidate) == 64:
                        return candidate.lower()
            direct = hex64_pattern.search(line)
            if direct:
                return direct.group(0).lower()
        return None

    def _resolve_asset_and_checksum(self, release: dict) -> tuple[dict, str]:
        assets = release.get("assets", []) or []
        manifest_asset = self._pick_manifest_asset(assets)
        if manifest_asset is not None:
            manifest_url = manifest_asset.get("browser_download_url")
            manifest_text = self._download_text(manifest_url)
            manifest = json.loads(manifest_text)

            asset_name = manifest.get("asset_name")
            sha256 = str(manifest.get("sha256", "")).strip().lower()
            if not asset_name or len(sha256) != 64:
                raise ValueError("Invalid manifest format: missing asset_name/sha256")

            asset = self._pick_package_asset(assets, preferred_name=asset_name)
            if asset is None:
                raise ValueError(f"Manifest asset not found in release: {asset_name}")
            return asset, sha256

        asset = self._pick_package_asset(assets)
        if asset is None:
            raise ValueError("No update package asset found (.zip/.7z/.exe)")

        asset_name = asset.get("name", "")
        checksum_asset = None
        for item in assets:
            name = str(item.get("name", "")).lower()
            if name.endswith(".sha256") or name.endswith(".sha256.txt"):
                checksum_asset = item
                break

        sha256 = None
        if checksum_asset is not None:
            checksum_text = self._download_text(checksum_asset.get("browser_download_url"))
            sha256 = self._extract_sha256_from_text(checksum_text, asset_name)

        if not sha256:
            body = str(release.get("body", ""))
            sha256 = self._extract_sha256_from_text(body, asset_name)

        if not sha256:
            raise ValueError("Missing SHA256 checksum in release assets/body")
        return asset, sha256

    def check_for_update(self) -> Optional[UpdateInfo]:
        """Return UpdateInfo if latest release is newer; otherwise None."""
        release = self._request_json(self._github_latest_release_url())
        latest_raw = release.get("tag_name") or release.get("name") or ""
        latest_version = self.normalize_version(latest_raw)
        if not latest_version:
            raise ValueError("Latest release has empty version")

        current_version = self.get_current_version()
        if self.compare_versions(latest_version, current_version) <= 0:
            self.logger.info(
                "No update available. current=%s latest=%s",
                current_version,
                latest_version,
            )
            return None

        asset, sha256 = self._resolve_asset_and_checksum(release)
        info = UpdateInfo(
            version=latest_version,
            release_name=str(release.get("name", f"v{latest_version}")),
            release_notes=str(release.get("body", "")).strip(),
            asset_name=str(asset.get("name", "")),
            asset_url=str(asset.get("browser_download_url", "")),
            sha256=sha256,
        )
        if not info.asset_name or not info.asset_url:
            raise ValueError("Resolved update asset is invalid")
        return info

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as fp:
            for chunk in iter(lambda: fp.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest().lower()

    def download_update(self, update_info: UpdateInfo) -> Path:
        """Download package and verify sha256, return local package path."""
        timeout = self.config_manager.get("update.request_timeout_sec", 20)
        tmp_dir = Path(tempfile.mkdtemp(prefix="larj_update_"))
        package_path = tmp_dir / update_info.asset_name

        with requests.get(update_info.asset_url, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            with open(package_path, "wb") as out:
                for chunk in resp.iter_content(chunk_size=1024 * 512):
                    if chunk:
                        out.write(chunk)

        actual = self.compute_sha256(package_path)
        expected = update_info.sha256.lower()
        if actual != expected:
            try:
                package_path.unlink(missing_ok=True)
            except OSError:
                self.logger.warning("Failed to delete invalid package: %s", package_path)
            raise ValueError(f"SHA256 mismatch. expected={expected} actual={actual}")

        self.logger.info("Downloaded update package: %s", package_path)
        return package_path
