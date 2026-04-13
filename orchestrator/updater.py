"""Auto-update system for AI Orchestrator from GitHub Releases."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from .version import Version, VersionInfo, get_version_manager, ReleaseChannel


class UpdateStatus(Enum):
    """Update check status."""

    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    UPDATE_REQUIRED = "update_required"
    CHECK_FAILED = "check_failed"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    RESTART_REQUIRED = "restart_required"


@dataclass
class ReleaseAsset:
    """GitHub release asset information."""

    name: str
    download_url: str
    size: int
    content_type: str
    browser_download_url: str


@dataclass
class ReleaseInfo:
    """GitHub release information."""

    tag_name: str
    name: str
    body: str
    published_at: str
    prerelease: bool
    draft: bool
    html_url: str
    assets: List[ReleaseAsset] = field(default_factory=list)

    @property
    def version(self) -> Version:
        """Parse version from tag name."""
        tag = self.tag_name
        if tag.startswith("v"):
            tag = tag[1:]
        return Version.parse(tag)

    @classmethod
    def from_github_api(cls, data: Dict[str, Any]) -> "ReleaseInfo":
        """Create from GitHub API response."""
        assets = []
        for asset_data in data.get("assets", []):
            assets.append(ReleaseAsset(
                name=asset_data.get("name", ""),
                download_url=asset_data.get("url", ""),
                size=asset_data.get("size", 0),
                content_type=asset_data.get("content_type", ""),
                browser_download_url=asset_data.get("browser_download_url", ""),
            ))

        return cls(
            tag_name=data.get("tag_name", ""),
            name=data.get("name", ""),
            body=data.get("body", ""),
            published_at=data.get("published_at", ""),
            prerelease=data.get("prerelease", False),
            draft=data.get("draft", False),
            html_url=data.get("html_url", ""),
            assets=assets,
        )


@dataclass
class UpdateResult:
    """Result of an update operation."""

    status: UpdateStatus
    current_version: str
    latest_version: Optional[str] = None
    release_info: Optional[ReleaseInfo] = None
    download_path: Optional[Path] = None
    error_message: Optional[str] = None
    progress: float = 0.0


@dataclass
class UpdateConfig:
    """Configuration for the updater."""

    github_owner: str = "hawk-ai"
    github_repo: str = "ai-orchestrator"
    check_interval_hours: int = 24
    auto_download: bool = False
    auto_install: bool = False
    include_prereleases: bool = False
    asset_pattern: str = "ai-orchestrator-{version}-win64.exe"
    cache_dir: Optional[Path] = None
    timeout_seconds: int = 30


class Updater:
    """Manages automatic updates from GitHub Releases."""

    GITHUB_API_URL = "https://api.github.com"

    def __init__(
        self,
        config: Optional[UpdateConfig] = None,
        root_path: Optional[Path] = None,
    ):
        """Initialize updater."""
        self.config = config or UpdateConfig()
        self.root_path = root_path or Path(__file__).parent.parent
        self.version_manager = get_version_manager(self.root_path)

        # Cache directory for downloads
        if self.config.cache_dir:
            self.cache_dir = self.config.cache_dir
        else:
            self.cache_dir = Path.home() / ".ai-orchestrator" / "updates"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Last check timestamp file
        self.last_check_file = self.cache_dir / "last_check.json"

        self._progress_callback: Optional[Callable[[float, str], None]] = None
        self._cancel_requested = False

    @property
    def current_version(self) -> Version:
        """Get current application version."""
        return self.version_manager.version

    def set_progress_callback(
        self, callback: Optional[Callable[[float, str], None]]
    ) -> None:
        """Set progress callback for download/install operations."""
        self._progress_callback = callback

    def cancel(self) -> None:
        """Request cancellation of current operation."""
        self._cancel_requested = True

    def _report_progress(self, progress: float, message: str) -> None:
        """Report progress to callback."""
        if self._progress_callback:
            self._progress_callback(progress, message)

    def _make_api_request(self, endpoint: str) -> Dict[str, Any]:
        """Make a request to GitHub API."""
        url = f"{self.GITHUB_API_URL}{endpoint}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"AI-Orchestrator/{self.current_version}",
        }

        request = Request(url, headers=headers)

        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            raise UpdateError(f"GitHub API error: {e.code} {e.reason}")
        except URLError as e:
            raise UpdateError(f"Network error: {e.reason}")
        except json.JSONDecodeError:
            raise UpdateError("Invalid response from GitHub")

    def get_releases(self, per_page: int = 10) -> List[ReleaseInfo]:
        """Fetch list of releases from GitHub."""
        endpoint = f"/repos/{self.config.github_owner}/{self.config.github_repo}/releases"
        endpoint += f"?per_page={per_page}"

        data = self._make_api_request(endpoint)

        releases = []
        for release_data in data:
            release = ReleaseInfo.from_github_api(release_data)

            # Skip drafts
            if release.draft:
                continue

            # Skip prereleases unless configured
            if release.prerelease and not self.config.include_prereleases:
                continue

            releases.append(release)

        return releases

    def get_latest_release(self) -> Optional[ReleaseInfo]:
        """Get the latest applicable release."""
        if self.config.include_prereleases:
            # Need to check all releases
            releases = self.get_releases(per_page=5)
            return releases[0] if releases else None
        else:
            # Use latest endpoint
            endpoint = f"/repos/{self.config.github_owner}/{self.config.github_repo}/releases/latest"
            try:
                data = self._make_api_request(endpoint)
                return ReleaseInfo.from_github_api(data)
            except UpdateError:
                return None

    def check_for_updates(self) -> UpdateResult:
        """Check if updates are available."""
        self._cancel_requested = False
        self._report_progress(0.0, "Checking for updates...")

        try:
            latest = self.get_latest_release()

            if latest is None:
                return UpdateResult(
                    status=UpdateStatus.CHECK_FAILED,
                    current_version=str(self.current_version),
                    error_message="No releases found",
                )

            self._report_progress(0.5, "Comparing versions...")

            latest_version = latest.version

            if latest_version > self.current_version:
                self._report_progress(1.0, "Update available!")
                return UpdateResult(
                    status=UpdateStatus.UPDATE_AVAILABLE,
                    current_version=str(self.current_version),
                    latest_version=str(latest_version),
                    release_info=latest,
                )
            else:
                self._report_progress(1.0, "Up to date")
                return UpdateResult(
                    status=UpdateStatus.UP_TO_DATE,
                    current_version=str(self.current_version),
                    latest_version=str(latest_version),
                    release_info=latest,
                )

        except UpdateError as e:
            return UpdateResult(
                status=UpdateStatus.CHECK_FAILED,
                current_version=str(self.current_version),
                error_message=str(e),
            )

        finally:
            self._save_last_check()

    def _save_last_check(self) -> None:
        """Save last check timestamp."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "version": str(self.current_version),
        }
        with open(self.last_check_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def _load_last_check(self) -> Optional[datetime]:
        """Load last check timestamp."""
        if not self.last_check_file.exists():
            return None

        try:
            with open(self.last_check_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return datetime.fromisoformat(data["timestamp"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def should_check_for_updates(self) -> bool:
        """Check if enough time has passed since last check."""
        last_check = self._load_last_check()
        if last_check is None:
            return True

        hours_since = (datetime.now() - last_check).total_seconds() / 3600
        return hours_since >= self.config.check_interval_hours

    def find_asset(self, release: ReleaseInfo) -> Optional[ReleaseAsset]:
        """Find the appropriate asset for current platform."""
        # Build expected asset name
        version_str = str(release.version)
        expected_name = self.config.asset_pattern.format(version=version_str)

        for asset in release.assets:
            if asset.name == expected_name:
                return asset

        # Fallback: look for .exe files
        for asset in release.assets:
            if asset.name.endswith(".exe") and "win" in asset.name.lower():
                return asset

        return None

    def download_update(
        self, release: ReleaseInfo, asset: Optional[ReleaseAsset] = None
    ) -> UpdateResult:
        """Download update package."""
        self._cancel_requested = False

        if asset is None:
            asset = self.find_asset(release)

        if asset is None:
            return UpdateResult(
                status=UpdateStatus.CHECK_FAILED,
                current_version=str(self.current_version),
                latest_version=str(release.version),
                error_message="No suitable download found for your platform",
            )

        download_path = self.cache_dir / asset.name
        self._report_progress(0.0, f"Downloading {asset.name}...")

        try:
            headers = {
                "Accept": "application/octet-stream",
                "User-Agent": f"AI-Orchestrator/{self.current_version}",
            }

            request = Request(asset.browser_download_url, headers=headers)

            with urlopen(request, timeout=self.config.timeout_seconds * 10) as response:
                total_size = asset.size or int(response.headers.get("content-length", 0))
                downloaded = 0
                chunk_size = 8192

                with open(download_path, "wb") as f:
                    while True:
                        if self._cancel_requested:
                            download_path.unlink(missing_ok=True)
                            return UpdateResult(
                                status=UpdateStatus.CHECK_FAILED,
                                current_version=str(self.current_version),
                                error_message="Download cancelled",
                            )

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            progress = downloaded / total_size
                            self._report_progress(
                                progress,
                                f"Downloading... {downloaded // 1024}KB / {total_size // 1024}KB",
                            )

            self._report_progress(1.0, "Download complete!")

            return UpdateResult(
                status=UpdateStatus.DOWNLOADING,
                current_version=str(self.current_version),
                latest_version=str(release.version),
                release_info=release,
                download_path=download_path,
                progress=1.0,
            )

        except (HTTPError, URLError) as e:
            download_path.unlink(missing_ok=True)
            return UpdateResult(
                status=UpdateStatus.CHECK_FAILED,
                current_version=str(self.current_version),
                error_message=f"Download failed: {e}",
            )

    def verify_download(self, download_path: Path, expected_hash: Optional[str] = None) -> bool:
        """Verify downloaded file integrity."""
        if not download_path.exists():
            return False

        if expected_hash:
            sha256 = hashlib.sha256()
            with open(download_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)

            return sha256.hexdigest() == expected_hash

        # Basic check: file exists and has content
        return download_path.stat().st_size > 0

    def install_update(self, download_path: Path) -> UpdateResult:
        """Install downloaded update."""
        self._cancel_requested = False
        self._report_progress(0.0, "Preparing installation...")

        if not download_path.exists():
            return UpdateResult(
                status=UpdateStatus.CHECK_FAILED,
                current_version=str(self.current_version),
                error_message="Download file not found",
            )

        try:
            # Create backup of current executable
            current_exe = Path(sys.executable)
            if current_exe.suffix == ".exe":
                backup_path = current_exe.with_suffix(".exe.bak")
                self._report_progress(0.2, "Creating backup...")

                if backup_path.exists():
                    backup_path.unlink()

            self._report_progress(0.5, "Installing update...")

            # For Windows, we need to use a batch script to replace the running exe
            if sys.platform == "win32":
                self._create_windows_updater_script(download_path, current_exe)

            self._report_progress(1.0, "Installation prepared - restart required")

            return UpdateResult(
                status=UpdateStatus.RESTART_REQUIRED,
                current_version=str(self.current_version),
                download_path=download_path,
            )

        except Exception as e:
            return UpdateResult(
                status=UpdateStatus.CHECK_FAILED,
                current_version=str(self.current_version),
                error_message=f"Installation failed: {e}",
            )

    def _create_windows_updater_script(self, source: Path, target: Path) -> Path:
        """Create a batch script to update the executable on Windows."""
        script_path = self.cache_dir / "update_script.bat"

        script_content = f"""@echo off
echo Waiting for application to close...
timeout /t 2 /nobreak > nul

echo Backing up current version...
if exist "{target}.bak" del "{target}.bak"
if exist "{target}" move "{target}" "{target}.bak"

echo Installing new version...
copy "{source}" "{target}"

echo Starting updated application...
start "" "{target}"

echo Cleaning up...
timeout /t 5 /nobreak > nul
if exist "{source}" del "{source}"
del "%~f0"
"""

        with open(script_path, "w") as f:
            f.write(script_content)

        return script_path

    def apply_update_and_restart(self) -> None:
        """Apply pending update and restart application."""
        script_path = self.cache_dir / "update_script.bat"

        if not script_path.exists():
            raise UpdateError("No pending update to apply")

        if sys.platform == "win32":
            # Start the updater script and exit
            subprocess.Popen(
                ["cmd", "/c", str(script_path)],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            sys.exit(0)
        else:
            raise UpdateError("Auto-update only supported on Windows")

    def cleanup_old_downloads(self, max_age_days: int = 7) -> int:
        """Remove old downloaded files."""
        count = 0
        cutoff = time.time() - (max_age_days * 86400)

        for file in self.cache_dir.iterdir():
            if file.suffix in (".exe", ".msi", ".zip"):
                if file.stat().st_mtime < cutoff:
                    file.unlink()
                    count += 1

        return count


class UpdateError(Exception):
    """Update operation error."""

    pass


# Global updater instance
_updater: Optional[Updater] = None


def get_updater(
    config: Optional[UpdateConfig] = None,
    root_path: Optional[Path] = None,
) -> Updater:
    """Get or create global updater instance."""
    global _updater

    if _updater is None:
        _updater = Updater(config, root_path)

    return _updater


def check_for_updates() -> UpdateResult:
    """Convenience function to check for updates."""
    return get_updater().check_for_updates()


def download_and_install(release: ReleaseInfo) -> UpdateResult:
    """Download and install an update."""
    updater = get_updater()

    # Download
    result = updater.download_update(release)
    if result.status == UpdateStatus.CHECK_FAILED:
        return result

    # Install
    if result.download_path:
        return updater.install_update(result.download_path)

    return result
