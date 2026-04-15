"""Tests for version management module."""

import json
import pytest
from pathlib import Path
from datetime import datetime

from orchestrator.version import (
    Version,
    VersionInfo,
    VersionManager,
    ReleaseChannel,
    load_changelog,
    get_recent_changelog_markdown,
    get_version_manager,
    get_version,
    get_version_info,
)


class TestVersion:
    """Tests for Version class."""

    def test_version_str(self):
        """Test version string representation."""
        v = Version(1, 2, 3)
        assert str(v) == "1.2.3"

    def test_version_str_with_prerelease(self):
        """Test version string with prerelease."""
        v = Version(1, 2, 3, prerelease="beta.1")
        assert str(v) == "1.2.3-beta.1"

    def test_version_str_with_build(self):
        """Test version string with build metadata."""
        v = Version(1, 2, 3, build="abc123")
        assert str(v) == "1.2.3+abc123"

    def test_version_str_full(self):
        """Test version string with prerelease and build."""
        v = Version(1, 2, 3, prerelease="alpha.1", build="20260413")
        assert str(v) == "1.2.3-alpha.1+20260413"

    def test_version_parse_simple(self):
        """Test parsing simple version string."""
        v = Version.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease is None
        assert v.build is None

    def test_version_parse_with_prerelease(self):
        """Test parsing version with prerelease."""
        v = Version.parse("2.0.0-beta.1")
        assert v.major == 2
        assert v.minor == 0
        assert v.patch == 0
        assert v.prerelease == "beta.1"

    def test_version_parse_with_build(self):
        """Test parsing version with build."""
        v = Version.parse("1.0.0+build.123")
        assert v.major == 1
        assert v.build == "build.123"

    def test_version_parse_full(self):
        """Test parsing full version string."""
        v = Version.parse("3.1.4-rc.2+sha.abc123")
        assert v.major == 3
        assert v.minor == 1
        assert v.patch == 4
        assert v.prerelease == "rc.2"
        assert v.build == "sha.abc123"

    def test_version_parse_invalid(self):
        """Test parsing invalid version string."""
        with pytest.raises(ValueError):
            Version.parse("invalid")

    def test_version_parse_invalid_format(self):
        """Test parsing invalid format."""
        with pytest.raises(ValueError):
            Version.parse("1.2")

    def test_version_comparison_equal(self):
        """Test version equality."""
        v1 = Version(1, 2, 3)
        v2 = Version(1, 2, 3)
        assert v1 == v2

    def test_version_comparison_less_than(self):
        """Test version less than."""
        v1 = Version(1, 0, 0)
        v2 = Version(2, 0, 0)
        assert v1 < v2

    def test_version_comparison_minor(self):
        """Test version comparison with minor."""
        v1 = Version(1, 1, 0)
        v2 = Version(1, 2, 0)
        assert v1 < v2

    def test_version_comparison_patch(self):
        """Test version comparison with patch."""
        v1 = Version(1, 0, 1)
        v2 = Version(1, 0, 2)
        assert v1 < v2

    def test_version_prerelease_lower(self):
        """Test prerelease has lower precedence than release."""
        v1 = Version(1, 0, 0, prerelease="alpha")
        v2 = Version(1, 0, 0)
        assert v1 < v2

    def test_version_prerelease_comparison(self):
        """Test prerelease comparison."""
        v1 = Version(1, 0, 0, prerelease="alpha")
        v2 = Version(1, 0, 0, prerelease="beta")
        assert v1 < v2

    def test_version_prerelease_numeric_comparison(self):
        """Test semver prerelease numeric comparison."""
        v1 = Version.parse("1.0.0-alpha.2")
        v2 = Version.parse("1.0.0-alpha.10")
        assert v1 < v2

    def test_version_greater_than(self):
        """Test version greater than."""
        v1 = Version(2, 0, 0)
        v2 = Version(1, 0, 0)
        assert v1 > v2

    def test_version_le(self):
        """Test version less than or equal."""
        v1 = Version(1, 0, 0)
        v2 = Version(1, 0, 0)
        assert v1 <= v2

    def test_version_ge(self):
        """Test version greater than or equal."""
        v1 = Version(1, 0, 0)
        v2 = Version(1, 0, 0)
        assert v1 >= v2

    def test_version_hash(self):
        """Test version hashing."""
        v1 = Version(1, 2, 3)
        v2 = Version(1, 2, 3)
        assert hash(v1) == hash(v2)

    def test_bump_major(self):
        """Test bumping major version."""
        v = Version(1, 2, 3)
        new_v = v.bump_major()
        assert new_v == Version(2, 0, 0)

    def test_bump_minor(self):
        """Test bumping minor version."""
        v = Version(1, 2, 3)
        new_v = v.bump_minor()
        assert new_v == Version(1, 3, 0)

    def test_bump_patch(self):
        """Test bumping patch version."""
        v = Version(1, 2, 3)
        new_v = v.bump_patch()
        assert new_v == Version(1, 2, 4)

    def test_with_prerelease(self):
        """Test adding prerelease tag."""
        v = Version(1, 0, 0)
        new_v = v.with_prerelease("beta.1")
        assert str(new_v) == "1.0.0-beta.1"

    def test_with_build(self):
        """Test adding build metadata."""
        v = Version(1, 0, 0)
        new_v = v.with_build("sha123")
        assert str(new_v) == "1.0.0+sha123"

    def test_to_tuple(self):
        """Test converting to tuple."""
        v = Version(1, 2, 3)
        assert v.to_tuple() == (1, 2, 3)


class TestVersionInfo:
    """Tests for VersionInfo class."""

    def test_version_info_to_dict(self):
        """Test converting to dictionary."""
        info = VersionInfo(
            version=Version(1, 0, 0),
            channel=ReleaseChannel.STABLE,
            build_date="2026-04-13T00:00:00",
            commit_hash="abc123",
        )
        data = info.to_dict()

        assert data["version"] == "1.0.0"
        assert data["major"] == 1
        assert data["channel"] == "stable"
        assert data["commit_hash"] == "abc123"

    def test_version_info_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "version": "1.2.3",
            "major": 1,
            "minor": 2,
            "patch": 3,
            "channel": "beta",
            "build_date": "2026-04-13",
        }
        info = VersionInfo.from_dict(data)

        assert info.version == Version(1, 2, 3)
        assert info.channel == ReleaseChannel.BETA

    def test_version_info_from_dict_defaults(self):
        """Test creating from dict with defaults."""
        info = VersionInfo.from_dict({})

        assert info.version == Version(0, 1, 0)
        assert info.channel == ReleaseChannel.STABLE
        assert info.app_name == "AI Orchestrator"

    def test_version_info_from_dict_uses_version_string(self):
        """Test creating from dict using semantic version string."""
        info = VersionInfo.from_dict({"version": "2.3.4-beta.1", "channel": "beta"})

        assert info.version == Version(2, 3, 4, prerelease="beta.1")
        assert info.channel == ReleaseChannel.BETA


class TestVersionManager:
    """Tests for VersionManager class."""

    def test_version_manager_load_default(self, tmp_path):
        """Test loading default version when file missing."""
        manager = VersionManager(tmp_path)
        info = manager.load()

        assert info.version == Version(0, 1, 0)
        assert info.channel == ReleaseChannel.DEV

    def test_version_manager_save_and_load(self, tmp_path):
        """Test saving and loading version."""
        manager = VersionManager(tmp_path)

        info = VersionInfo(
            version=Version(2, 0, 0),
            channel=ReleaseChannel.BETA,
        )
        manager.save(info)

        # Load again
        manager2 = VersionManager(tmp_path)
        loaded = manager2.load()

        assert loaded.version == Version(2, 0, 0)
        assert loaded.channel == ReleaseChannel.BETA

    def test_version_manager_bump_patch(self, tmp_path):
        """Test bumping patch version."""
        manager = VersionManager(tmp_path)
        manager.save(VersionInfo(version=Version(1, 0, 0)))

        new_version = manager.bump("patch")

        assert new_version == Version(1, 0, 1)
        assert manager.version == Version(1, 0, 1)

    def test_version_manager_bump_minor(self, tmp_path):
        """Test bumping minor version."""
        manager = VersionManager(tmp_path)
        manager.save(VersionInfo(version=Version(1, 0, 0)))

        new_version = manager.bump("minor")

        assert new_version == Version(1, 1, 0)

    def test_version_manager_bump_major(self, tmp_path):
        """Test bumping major version."""
        manager = VersionManager(tmp_path)
        manager.save(VersionInfo(version=Version(1, 2, 3)))

        new_version = manager.bump("major")

        assert new_version == Version(2, 0, 0)

    def test_version_manager_bump_with_prerelease(self, tmp_path):
        """Test bumping with prerelease."""
        manager = VersionManager(tmp_path)
        manager.save(VersionInfo(version=Version(1, 0, 0)))

        new_version = manager.bump("minor", prerelease="beta.1")

        assert str(new_version) == "1.1.0-beta.1"

    def test_version_manager_set_version(self, tmp_path):
        """Test setting specific version."""
        manager = VersionManager(tmp_path)
        manager.save(VersionInfo(version=Version(1, 0, 0)))

        new_version = manager.set_version("3.0.0-rc.1")

        assert new_version == Version(3, 0, 0, prerelease="rc.1")

    def test_version_manager_set_commit_hash(self, tmp_path):
        """Test setting commit hash."""
        manager = VersionManager(tmp_path)
        manager.save(VersionInfo(version=Version(1, 0, 0)))

        manager.set_commit_hash("abc123def")

        assert manager.info.commit_hash == "abc123def"

    def test_version_manager_set_channel(self, tmp_path):
        """Test setting release channel."""
        manager = VersionManager(tmp_path)
        manager.save(VersionInfo(version=Version(1, 0, 0)))

        manager.set_channel(ReleaseChannel.STABLE)

        assert manager.info.channel == ReleaseChannel.STABLE

    def test_version_manager_version_string(self, tmp_path):
        """Test getting version string."""
        manager = VersionManager(tmp_path)
        manager.save(VersionInfo(version=Version(1, 2, 3)))

        assert manager.version_string == "1.2.3"

    def test_version_manager_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON file."""
        version_file = tmp_path / "version.json"
        version_file.write_text("invalid json")

        manager = VersionManager(tmp_path)
        info = manager.load()

        # Should return default
        assert info.version == Version(0, 1, 0)


class TestReleaseChannel:
    """Tests for ReleaseChannel enum."""

    def test_channel_values(self):
        """Test channel enum values."""
        assert ReleaseChannel.STABLE.value == "stable"
        assert ReleaseChannel.BETA.value == "beta"
        assert ReleaseChannel.ALPHA.value == "alpha"
        assert ReleaseChannel.DEV.value == "dev"


class TestChangelog:
    """Tests for changelog parsing helpers."""

    def test_load_changelog_entries(self, tmp_path):
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\n"
            "## [0.2.0] - 2026-04-14\n"
            "- Release polish\n\n"
            "## [0.1.0] - 2026-04-13\n"
            "- Initial release\n",
            encoding="utf-8",
        )

        entries = load_changelog(tmp_path)

        assert len(entries) == 2
        assert entries[0].version == "0.2.0"
        assert "Release polish" in entries[0].content

    def test_get_recent_changelog_markdown(self, tmp_path):
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\n"
            "## [0.2.0] - 2026-04-14\n"
            "- Release polish\n",
            encoding="utf-8",
        )

        content = get_recent_changelog_markdown(tmp_path, max_entries=1)

        assert "0.2.0" in content
        assert "Release polish" in content


class TestGlobalFunctions:
    """Tests for global helper functions."""

    def test_get_version_manager(self, tmp_path):
        """Test getting version manager."""
        manager = get_version_manager(tmp_path)
        assert manager is not None
        assert manager.root_path == tmp_path

    def test_get_version(self, tmp_path, monkeypatch):
        """Test getting version string."""
        # Create a version file in tmp_path
        version_file = tmp_path / "version.json"
        version_file.write_text(json.dumps({
            "version": "1.5.0",
            "major": 1,
            "minor": 5,
            "patch": 0,
        }))

        manager = get_version_manager(tmp_path)
        assert manager.version_string == "1.5.0"

    def test_get_version_info(self, tmp_path):
        """Test getting version info."""
        version_file = tmp_path / "version.json"
        version_file.write_text(json.dumps({
            "version": "2.0.0",
            "major": 2,
            "minor": 0,
            "patch": 0,
            "channel": "stable",
            "app_name": "Test App",
        }))

        manager = get_version_manager(tmp_path)
        info = manager.info

        assert info.version == Version(2, 0, 0)
        assert info.app_name == "Test App"
