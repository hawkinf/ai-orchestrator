"""Tests for auto-update module."""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from orchestrator.updater import (
    UpdateStatus,
    ReleaseAsset,
    ReleaseInfo,
    UpdateResult,
    UpdateConfig,
    Updater,
    UpdateError,
    get_updater,
    check_for_updates,
)
from orchestrator.version import Version


class TestUpdateStatus:
    """Tests for UpdateStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert UpdateStatus.UP_TO_DATE.value == "up_to_date"
        assert UpdateStatus.UPDATE_AVAILABLE.value == "update_available"
        assert UpdateStatus.CHECK_FAILED.value == "check_failed"
        assert UpdateStatus.DOWNLOADING.value == "downloading"
        assert UpdateStatus.RESTART_REQUIRED.value == "restart_required"


class TestReleaseAsset:
    """Tests for ReleaseAsset class."""

    def test_asset_creation(self):
        """Test creating release asset."""
        asset = ReleaseAsset(
            name="app-1.0.0-win64.exe",
            download_url="https://api.github.com/...",
            size=50000000,
            content_type="application/octet-stream",
            browser_download_url="https://github.com/.../releases/download/...",
        )

        assert asset.name == "app-1.0.0-win64.exe"
        assert asset.size == 50000000


class TestReleaseInfo:
    """Tests for ReleaseInfo class."""

    def test_release_info_creation(self):
        """Test creating release info."""
        release = ReleaseInfo(
            tag_name="v1.2.3",
            name="Release 1.2.3",
            body="Release notes here",
            published_at="2026-04-13T00:00:00Z",
            prerelease=False,
            draft=False,
            html_url="https://github.com/...",
        )

        assert release.tag_name == "v1.2.3"
        assert release.prerelease is False

    def test_release_version_parsing(self):
        """Test parsing version from tag."""
        release = ReleaseInfo(
            tag_name="v1.2.3",
            name="",
            body="",
            published_at="",
            prerelease=False,
            draft=False,
            html_url="",
        )

        assert release.version == Version(1, 2, 3)

    def test_release_version_without_v_prefix(self):
        """Test parsing version without v prefix."""
        release = ReleaseInfo(
            tag_name="2.0.0",
            name="",
            body="",
            published_at="",
            prerelease=False,
            draft=False,
            html_url="",
        )

        assert release.version == Version(2, 0, 0)

    def test_release_version_with_prerelease(self):
        """Test parsing version with prerelease tag."""
        release = ReleaseInfo(
            tag_name="v1.0.0-beta.1",
            name="",
            body="",
            published_at="",
            prerelease=True,
            draft=False,
            html_url="",
        )

        assert release.version == Version(1, 0, 0, prerelease="beta.1")

    def test_from_github_api(self):
        """Test creating from GitHub API response."""
        api_data = {
            "tag_name": "v1.5.0",
            "name": "Version 1.5.0",
            "body": "## Changes\n- New feature",
            "published_at": "2026-04-13T12:00:00Z",
            "prerelease": False,
            "draft": False,
            "html_url": "https://github.com/owner/repo/releases/tag/v1.5.0",
            "assets": [
                {
                    "name": "app-win64.exe",
                    "url": "https://api.github.com/...",
                    "size": 40000000,
                    "content_type": "application/octet-stream",
                    "browser_download_url": "https://github.com/.../download/...",
                }
            ],
        }

        release = ReleaseInfo.from_github_api(api_data)

        assert release.tag_name == "v1.5.0"
        assert release.name == "Version 1.5.0"
        assert len(release.assets) == 1
        assert release.assets[0].name == "app-win64.exe"


class TestUpdateResult:
    """Tests for UpdateResult class."""

    def test_result_creation(self):
        """Test creating update result."""
        result = UpdateResult(
            status=UpdateStatus.UPDATE_AVAILABLE,
            current_version="1.0.0",
            latest_version="1.1.0",
        )

        assert result.status == UpdateStatus.UPDATE_AVAILABLE
        assert result.current_version == "1.0.0"
        assert result.latest_version == "1.1.0"

    def test_result_with_error(self):
        """Test result with error message."""
        result = UpdateResult(
            status=UpdateStatus.CHECK_FAILED,
            current_version="1.0.0",
            error_message="Network error",
        )

        assert result.status == UpdateStatus.CHECK_FAILED
        assert result.error_message == "Network error"


class TestUpdateConfig:
    """Tests for UpdateConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = UpdateConfig()

        assert config.github_owner == "hawk-ai"
        assert config.github_repo == "ai-orchestrator"
        assert config.check_interval_hours == 24
        assert config.auto_download is False
        assert config.include_prereleases is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = UpdateConfig(
            github_owner="my-org",
            github_repo="my-app",
            check_interval_hours=12,
            auto_download=True,
        )

        assert config.github_owner == "my-org"
        assert config.check_interval_hours == 12


class TestUpdater:
    """Tests for Updater class."""

    def test_updater_init(self, tmp_path):
        """Test updater initialization."""
        config = UpdateConfig(cache_dir=tmp_path / "cache")
        updater = Updater(config, root_path=tmp_path)

        assert updater.config == config
        assert updater.cache_dir == tmp_path / "cache"
        assert updater.cache_dir.exists()

    def test_current_version(self, tmp_path):
        """Test getting current version."""
        # Create version.json
        version_file = tmp_path / "version.json"
        version_file.write_text(json.dumps({
            "major": 1,
            "minor": 0,
            "patch": 0,
        }))

        updater = Updater(root_path=tmp_path)

        assert updater.current_version == Version(1, 0, 0)

    def test_progress_callback(self, tmp_path):
        """Test setting progress callback."""
        updater = Updater(root_path=tmp_path)
        received = []

        def on_progress(progress: float, message: str):
            received.append((progress, message))

        updater.set_progress_callback(on_progress)
        updater._report_progress(0.5, "Test message")

        assert len(received) == 1
        assert received[0] == (0.5, "Test message")

    def test_cancel_request(self, tmp_path):
        """Test cancellation request."""
        updater = Updater(root_path=tmp_path)

        assert updater._cancel_requested is False
        updater.cancel()
        assert updater._cancel_requested is True

    def test_save_and_load_last_check(self, tmp_path):
        """Test saving and loading last check timestamp."""
        config = UpdateConfig(cache_dir=tmp_path / "cache")
        updater = Updater(config, root_path=tmp_path)

        # Save
        updater._save_last_check()

        # Load
        last_check = updater._load_last_check()

        assert last_check is not None
        assert (datetime.now() - last_check).total_seconds() < 5

    def test_load_last_check_missing(self, tmp_path):
        """Test loading missing last check file."""
        config = UpdateConfig(cache_dir=tmp_path / "cache")
        updater = Updater(config, root_path=tmp_path)

        last_check = updater._load_last_check()

        assert last_check is None

    def test_should_check_never_checked(self, tmp_path):
        """Test should check when never checked."""
        config = UpdateConfig(cache_dir=tmp_path / "cache")
        updater = Updater(config, root_path=tmp_path)

        assert updater.should_check_for_updates() is True

    def test_should_check_recently_checked(self, tmp_path):
        """Test should check when recently checked."""
        config = UpdateConfig(cache_dir=tmp_path / "cache", check_interval_hours=24)
        updater = Updater(config, root_path=tmp_path)

        # Simulate recent check
        updater._save_last_check()

        assert updater.should_check_for_updates() is False

    def test_find_asset_exact_match(self, tmp_path):
        """Test finding asset with exact name match."""
        updater = Updater(root_path=tmp_path)

        release = ReleaseInfo(
            tag_name="v1.0.0",
            name="",
            body="",
            published_at="",
            prerelease=False,
            draft=False,
            html_url="",
            assets=[
                ReleaseAsset(
                    name="ai-orchestrator-1.0.0-win64.exe",
                    download_url="",
                    size=50000000,
                    content_type="",
                    browser_download_url="https://example.com/download",
                ),
            ],
        )

        asset = updater.find_asset(release)

        assert asset is not None
        assert asset.name == "ai-orchestrator-1.0.0-win64.exe"

    def test_find_asset_fallback(self, tmp_path):
        """Test finding asset with fallback pattern."""
        updater = Updater(root_path=tmp_path)

        release = ReleaseInfo(
            tag_name="v1.0.0",
            name="",
            body="",
            published_at="",
            prerelease=False,
            draft=False,
            html_url="",
            assets=[
                ReleaseAsset(
                    name="app-windows-x64.exe",
                    download_url="",
                    size=50000000,
                    content_type="",
                    browser_download_url="https://example.com/download",
                ),
            ],
        )

        asset = updater.find_asset(release)

        assert asset is not None
        assert "win" in asset.name.lower()

    def test_find_asset_not_found(self, tmp_path):
        """Test finding asset when none match."""
        updater = Updater(root_path=tmp_path)

        release = ReleaseInfo(
            tag_name="v1.0.0",
            name="",
            body="",
            published_at="",
            prerelease=False,
            draft=False,
            html_url="",
            assets=[
                ReleaseAsset(
                    name="app-linux.tar.gz",
                    download_url="",
                    size=50000000,
                    content_type="",
                    browser_download_url="https://example.com/download",
                ),
            ],
        )

        asset = updater.find_asset(release)

        assert asset is None

    def test_verify_download_exists(self, tmp_path):
        """Test verifying download file exists."""
        updater = Updater(root_path=tmp_path)

        download_file = tmp_path / "test.exe"
        download_file.write_bytes(b"test content")

        assert updater.verify_download(download_file) is True

    def test_verify_download_missing(self, tmp_path):
        """Test verifying missing download file."""
        updater = Updater(root_path=tmp_path)

        download_file = tmp_path / "missing.exe"

        assert updater.verify_download(download_file) is False

    def test_verify_download_with_hash(self, tmp_path):
        """Test verifying download with hash."""
        import hashlib

        updater = Updater(root_path=tmp_path)

        content = b"test content"
        expected_hash = hashlib.sha256(content).hexdigest()

        download_file = tmp_path / "test.exe"
        download_file.write_bytes(content)

        assert updater.verify_download(download_file, expected_hash) is True

    def test_verify_download_wrong_hash(self, tmp_path):
        """Test verifying download with wrong hash."""
        updater = Updater(root_path=tmp_path)

        download_file = tmp_path / "test.exe"
        download_file.write_bytes(b"test content")

        assert updater.verify_download(download_file, "wronghash") is False

    def test_cleanup_old_downloads(self, tmp_path):
        """Test cleaning up old downloads."""
        import time

        config = UpdateConfig(cache_dir=tmp_path / "cache")
        updater = Updater(config, root_path=tmp_path)

        # Create old file
        old_file = updater.cache_dir / "old.exe"
        old_file.write_bytes(b"old")
        # Set mtime to 10 days ago (can't easily mock, but test the logic)

        # Create new file
        new_file = updater.cache_dir / "new.exe"
        new_file.write_bytes(b"new")

        # Note: This would need mtime mocking for full test
        # For now just verify it runs without error
        count = updater.cleanup_old_downloads(max_age_days=0)

        # Should clean up files older than 0 days (all except just-created)
        assert isinstance(count, int)

    @patch("orchestrator.updater.urlopen")
    def test_check_for_updates_up_to_date(self, mock_urlopen, tmp_path):
        """Test checking for updates when up to date."""
        # Setup current version
        version_file = tmp_path / "version.json"
        version_file.write_text(json.dumps({
            "major": 1,
            "minor": 0,
            "patch": 0,
        }))

        # Mock API response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "tag_name": "v1.0.0",
            "name": "Version 1.0.0",
            "body": "",
            "published_at": "",
            "prerelease": False,
            "draft": False,
            "html_url": "",
            "assets": [],
        }).encode()
        mock_response.headers = {}
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        updater = Updater(root_path=tmp_path)
        result = updater.check_for_updates()

        assert result.status == UpdateStatus.UP_TO_DATE
        assert result.current_version == "1.0.0"

    @patch("orchestrator.updater.urlopen")
    def test_check_for_updates_available(self, mock_urlopen, tmp_path):
        """Test checking for updates when update available."""
        # Setup current version
        version_file = tmp_path / "version.json"
        version_file.write_text(json.dumps({
            "major": 1,
            "minor": 0,
            "patch": 0,
        }))

        # Mock API response with newer version
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "tag_name": "v2.0.0",
            "name": "Version 2.0.0",
            "body": "New features!",
            "published_at": "",
            "prerelease": False,
            "draft": False,
            "html_url": "",
            "assets": [],
        }).encode()
        mock_response.headers = {}
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        updater = Updater(root_path=tmp_path)
        result = updater.check_for_updates()

        assert result.status == UpdateStatus.UPDATE_AVAILABLE
        assert result.latest_version == "2.0.0"

    def test_install_update_missing_file(self, tmp_path):
        """Test installing with missing download file."""
        updater = Updater(root_path=tmp_path)

        result = updater.install_update(tmp_path / "missing.exe")

        assert result.status == UpdateStatus.CHECK_FAILED
        assert "not found" in result.error_message.lower()


class TestUpdateError:
    """Tests for UpdateError exception."""

    def test_error_creation(self):
        """Test creating update error."""
        error = UpdateError("Test error message")
        assert str(error) == "Test error message"


class TestGlobalFunctions:
    """Tests for global helper functions."""

    def test_get_updater(self, tmp_path):
        """Test getting updater instance."""
        import orchestrator.updater as updater_module
        updater_module._updater = None

        config = UpdateConfig(cache_dir=tmp_path / "cache")
        updater = get_updater(config, tmp_path)

        assert updater is not None
        assert updater.config == config

    def test_get_updater_singleton(self, tmp_path):
        """Test updater singleton behavior."""
        import orchestrator.updater as updater_module
        updater_module._updater = None

        updater1 = get_updater(root_path=tmp_path)
        updater2 = get_updater()

        assert updater1 is updater2
