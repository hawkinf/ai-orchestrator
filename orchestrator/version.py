"""Semantic versioning and version management for AI Orchestrator."""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


class ReleaseChannel(Enum):
    """Release channel for updates."""

    STABLE = "stable"
    BETA = "beta"
    ALPHA = "alpha"
    DEV = "dev"


@dataclass
class Version:
    """Semantic version representation."""

    major: int = 0
    minor: int = 1
    patch: int = 0
    prerelease: Optional[str] = None
    build: Optional[str] = None

    def __str__(self) -> str:
        """Return version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __lt__(self, other: "Version") -> bool:
        """Compare versions."""
        if not isinstance(other, Version):
            return NotImplemented

        # Compare major.minor.patch
        self_tuple = (self.major, self.minor, self.patch)
        other_tuple = (other.major, other.minor, other.patch)

        if self_tuple != other_tuple:
            return self_tuple < other_tuple

        # Prerelease versions have lower precedence
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        if self.prerelease and other.prerelease:
            return self.prerelease < other.prerelease

        return False

    def __le__(self, other: "Version") -> bool:
        return self == other or self < other

    def __gt__(self, other: "Version") -> bool:
        return not self <= other

    def __ge__(self, other: "Version") -> bool:
        return not self < other

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.prerelease))

    @classmethod
    def parse(cls, version_string: str) -> "Version":
        """Parse a version string into a Version object."""
        # Pattern: major.minor.patch[-prerelease][+build]
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.]+))?(?:\+([a-zA-Z0-9.]+))?$"
        match = re.match(pattern, version_string.strip())

        if not match:
            raise ValueError(f"Invalid version string: {version_string}")

        major, minor, patch, prerelease, build = match.groups()

        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=prerelease,
            build=build,
        )

    def bump_major(self) -> "Version":
        """Return a new version with major incremented."""
        return Version(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> "Version":
        """Return a new version with minor incremented."""
        return Version(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> "Version":
        """Return a new version with patch incremented."""
        return Version(major=self.major, minor=self.minor, patch=self.patch + 1)

    def with_prerelease(self, prerelease: Optional[str]) -> "Version":
        """Return a new version with prerelease tag."""
        return Version(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            prerelease=prerelease,
            build=self.build,
        )

    def with_build(self, build: Optional[str]) -> "Version":
        """Return a new version with build metadata."""
        return Version(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            prerelease=self.prerelease,
            build=build,
        )

    def to_tuple(self) -> Tuple[int, int, int]:
        """Return version as tuple (major, minor, patch)."""
        return (self.major, self.minor, self.patch)


@dataclass
class VersionInfo:
    """Complete version information for the application."""

    version: Version
    channel: ReleaseChannel = ReleaseChannel.STABLE
    build_date: Optional[str] = None
    commit_hash: Optional[str] = None
    app_name: str = "AI Orchestrator"
    author: str = "Hawk Informatica"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "version": str(self.version),
            "major": self.version.major,
            "minor": self.version.minor,
            "patch": self.version.patch,
            "prerelease": self.version.prerelease,
            "build": self.version.build,
            "channel": self.channel.value,
            "build_date": self.build_date,
            "commit_hash": self.commit_hash,
            "app_name": self.app_name,
            "author": self.author,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VersionInfo":
        """Create from dictionary."""
        version = Version(
            major=data.get("major", 0),
            minor=data.get("minor", 1),
            patch=data.get("patch", 0),
            prerelease=data.get("prerelease"),
            build=data.get("build"),
        )

        channel_str = data.get("channel", "stable")
        try:
            channel = ReleaseChannel(channel_str)
        except ValueError:
            channel = ReleaseChannel.STABLE

        return cls(
            version=version,
            channel=channel,
            build_date=data.get("build_date"),
            commit_hash=data.get("commit_hash"),
            app_name=data.get("app_name", "AI Orchestrator"),
            author=data.get("author", "Hawk Informatica"),
        )


class VersionManager:
    """Manages version information and version.json file."""

    def __init__(self, root_path: Optional[Path] = None):
        """Initialize version manager."""
        if root_path is None:
            root_path = Path(__file__).parent.parent
        self.root_path = Path(root_path)
        self.version_file = self.root_path / "version.json"
        self._info: Optional[VersionInfo] = None

    @property
    def info(self) -> VersionInfo:
        """Get current version info, loading from file if needed."""
        if self._info is None:
            self._info = self.load()
        return self._info

    @property
    def version(self) -> Version:
        """Get current version."""
        return self.info.version

    @property
    def version_string(self) -> str:
        """Get version as string."""
        return str(self.version)

    def load(self) -> VersionInfo:
        """Load version info from version.json."""
        if self.version_file.exists():
            try:
                with open(self.version_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return VersionInfo.from_dict(data)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load version.json: {e}")

        # Return default version
        return VersionInfo(
            version=Version(0, 1, 0),
            channel=ReleaseChannel.DEV,
            build_date=datetime.now().isoformat(),
        )

    def save(self, info: Optional[VersionInfo] = None) -> None:
        """Save version info to version.json."""
        if info is not None:
            self._info = info

        if self._info is None:
            self._info = self.load()

        with open(self.version_file, "w", encoding="utf-8") as f:
            json.dump(self._info.to_dict(), f, indent=2)

    def bump(self, bump_type: str = "patch", prerelease: Optional[str] = None) -> Version:
        """Bump version and save."""
        info = self.info

        if bump_type == "major":
            new_version = info.version.bump_major()
        elif bump_type == "minor":
            new_version = info.version.bump_minor()
        else:
            new_version = info.version.bump_patch()

        if prerelease:
            new_version = new_version.with_prerelease(prerelease)

        info.version = new_version
        info.build_date = datetime.now().isoformat()

        self.save(info)
        return new_version

    def set_version(self, version_string: str) -> Version:
        """Set specific version and save."""
        version = Version.parse(version_string)
        info = self.info
        info.version = version
        info.build_date = datetime.now().isoformat()
        self.save(info)
        return version

    def set_commit_hash(self, commit_hash: str) -> None:
        """Set commit hash and save."""
        info = self.info
        info.commit_hash = commit_hash
        self.save(info)

    def set_channel(self, channel: ReleaseChannel) -> None:
        """Set release channel and save."""
        info = self.info
        info.channel = channel
        self.save(info)


# Global version manager instance
_version_manager: Optional[VersionManager] = None


def get_version_manager(root_path: Optional[Path] = None) -> VersionManager:
    """Get or create global version manager."""
    global _version_manager

    if _version_manager is None or (root_path and _version_manager.root_path != root_path):
        _version_manager = VersionManager(root_path)

    return _version_manager


def get_version() -> str:
    """Get current version string."""
    return get_version_manager().version_string


def get_version_info() -> VersionInfo:
    """Get current version info."""
    return get_version_manager().info


# Current version constants (for imports)
__version__ = "0.1.0"
__version_info__ = (0, 1, 0)
