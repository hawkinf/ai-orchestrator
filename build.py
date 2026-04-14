#!/usr/bin/env python3
"""Build, release and installer pipeline for AI Orchestrator."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from orchestrator.updater import UpdateConfig
from orchestrator.version import ReleaseChannel, get_recent_changelog_markdown, get_version_manager

ROOT_PATH = Path(__file__).parent


def get_version_info_path() -> Path:
    """Return the version resource file path."""
    return ROOT_PATH / "version_info.txt"


def get_version() -> str:
    """Get current version from the single source of truth."""
    return get_version_manager(ROOT_PATH).version_string


def get_build_logs_dir() -> Path:
    """Return the directory used for build logs."""
    logs_dir = ROOT_PATH / "dist" / "build-logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_release_dir(version: str) -> Path:
    """Return the release artifacts directory inside dist/."""
    release_dir = ROOT_PATH / "dist" / "releases" / f"v{version}"
    release_dir.mkdir(parents=True, exist_ok=True)
    return release_dir


def get_git_commit_hash() -> str | None:
    """Return the current git commit hash if available."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT_PATH,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def sync_version_metadata(channel: ReleaseChannel | None = None) -> None:
    """Update version.json metadata before a build."""
    manager = get_version_manager(ROOT_PATH)
    info = manager.info
    info.build_date = datetime.now().isoformat(timespec="seconds")
    info.commit_hash = get_git_commit_hash()
    if channel is not None:
        info.channel = channel
    manager.save(info)


def update_version_info() -> None:
    """Update version_info.txt with current version metadata."""
    version = get_version()
    parts = version.split(".")
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 1
    patch = int(parts[2].split("-")[0]) if len(parts) > 2 else 0

    content = f'''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', 'Hawk Informatica'),
            StringStruct('FileDescription', 'AI Orchestrator - Desktop Product Release'),
            StringStruct('FileVersion', '{version}'),
            StringStruct('InternalName', 'AIOrchestrator'),
            StringStruct('LegalCopyright', '(c) {datetime.now().year} Hawk Informatica. All rights reserved.'),
            StringStruct('OriginalFilename', 'AIOrchestrator.exe'),
            StringStruct('ProductName', 'AI Orchestrator'),
            StringStruct('ProductVersion', '{version}'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
'''
    get_version_info_path().write_text(content, encoding="utf-8", newline="\n")
    print(f"Updated version_info.txt to version {version}")


def validate_version_info_file(version_info_path: Path) -> None:
    """Validate version resource file encoding and contents for PyInstaller."""
    if not version_info_path.exists():
        raise FileNotFoundError(f"Version info file not found: {version_info_path}")

    raw = version_info_path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Version info file is not valid UTF-8: {version_info_path}") from exc

    non_ascii = sorted({char for char in text if ord(char) > 127})
    if non_ascii:
        chars = ", ".join(repr(char) for char in non_ascii)
        raise ValueError(
            f"Version info file contains non-ASCII characters that are unsafe for PyInstaller: {chars}"
        )

    required_markers = ["VSVersionInfo(", "StringStruct('FileVersion'", "StringStruct('ProductVersion'"]
    missing_markers = [marker for marker in required_markers if marker not in text]
    if missing_markers:
        markers = ", ".join(missing_markers)
        raise ValueError(f"Version info file is missing required markers: {markers}")


def format_command(cmd: list[str]) -> str:
    """Format a subprocess command for readable logging."""
    return subprocess.list2cmdline([str(part) for part in cmd])


def detect_spec_build_mode(spec_file: Path) -> str:
    """Infer PyInstaller packaging mode from a spec file."""
    spec_text = spec_file.read_text(encoding="utf-8")
    has_exe = "EXE(" in spec_text
    has_collect = "COLLECT(" in spec_text

    if has_exe and not has_collect:
        return "onefile"
    if has_exe and has_collect:
        return "onedir"
    return "unknown"


def validate_spec_file(spec_file: Path) -> str:
    """Validate the expected structure and required assets of the spec file."""
    if not spec_file.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_file}")

    spec_text = spec_file.read_text(encoding="utf-8")
    required_markers = ["Analysis(", "EXE("]
    missing_markers = [marker for marker in required_markers if marker not in spec_text]
    if missing_markers:
        markers = ", ".join(missing_markers)
        raise ValueError(f"Spec file is missing required sections: {markers}")

    required_paths = [
        ROOT_PATH / "version.json",
        ROOT_PATH / "update_config.json",
        ROOT_PATH / "CHANGELOG.md",
        ROOT_PATH / "config.yaml",
        ROOT_PATH / "prompts",
    ]
    missing_paths = [str(path) for path in required_paths if not path.exists()]
    if missing_paths:
        paths = ", ".join(missing_paths)
        raise FileNotFoundError(f"Spec file references missing required paths: {paths}")

    version_info_path = get_version_info_path()
    if version_info_path.exists():
        validate_version_info_file(version_info_path)

    return detect_spec_build_mode(spec_file)


def resolve_build_target(target: str | None = None) -> Path:
    """Resolve the PyInstaller build target."""
    if target:
        return (ROOT_PATH / target).resolve() if not Path(target).is_absolute() else Path(target)

    spec_file = ROOT_PATH / "ai_orchestrator.spec"
    if spec_file.exists():
        return spec_file

    return ROOT_PATH / "main.py"


def build_pyinstaller_command(target: Path, debug: bool = False, onefile: bool = True) -> tuple[list[str], str]:
    """Build the PyInstaller command while respecting spec-vs-script rules."""
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
    ]

    if debug:
        cmd.append("--debug=all")

    if target.suffix.lower() == ".spec":
        build_mode = validate_spec_file(target)
        cmd.append(str(target))
        return cmd, build_mode

    build_mode = "onefile" if onefile else "onedir"
    cmd.append(f"--{build_mode}")
    cmd.extend([
        "--name=AIOrchestrator",
        "--windowed",
        f"--add-data={ROOT_PATH / 'version.json'};.",
        f"--add-data={ROOT_PATH / 'update_config.json'};.",
        f"--add-data={ROOT_PATH / 'CHANGELOG.md'};.",
        f"--version-file={get_version_info_path()}",
        str(target),
    ])
    return cmd, build_mode


def run_logged_command(cmd: list[str], log_prefix: str) -> subprocess.CompletedProcess[str]:
    """Run a command and persist stdout/stderr into dist/build-logs/."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = get_build_logs_dir() / f"{log_prefix}_{timestamp}.log"
    result = subprocess.run(
        cmd,
        cwd=ROOT_PATH,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log_path.write_text(
        "\n".join(
            [
                f"Command: {format_command(cmd)}",
                "",
                "STDOUT:",
                result.stdout,
                "",
                "STDERR:",
                result.stderr,
            ]
        ),
        encoding="utf-8",
    )
    print(f"Log file: {log_path}")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result


def clean() -> None:
    """Clean build artifacts."""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    files_to_clean = ["*.pyc", "*.pyo", "*.spec.bak"]

    for dir_name in dirs_to_clean:
        dir_path = ROOT_PATH / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Cleaned: {dir_path}")

    for pattern in files_to_clean:
        for file_path in ROOT_PATH.rglob(pattern):
            file_path.unlink()
            print(f"Removed: {file_path}")

    print("Clean complete!")


def build_exe(debug: bool = False, onefile: bool = True, target: str | None = None) -> None:
    """Build the executable using PyInstaller."""
    version = get_version()
    print(f"Building AI Orchestrator v{version}...")

    sync_version_metadata(ReleaseChannel.DEV if debug else None)
    update_version_info()

    resolved_target = resolve_build_target(target)
    cmd, build_mode = build_pyinstaller_command(resolved_target, debug=debug, onefile=onefile)

    print(f"Build target: {resolved_target}")
    print(f"App version: {version}")
    print(f"Detected build mode: {build_mode}")
    if resolved_target.suffix.lower() == ".spec":
        print(f"Spec file: {resolved_target}")
        if not onefile:
            print("Note: --onedir was requested, but packaging mode is controlled by the spec file and CLI mode flags were skipped.")

    result = run_logged_command(cmd, "build")
    if result.returncode == 0:
        print("\nBuild successful!")
        if build_mode == "onedir":
            print(f"Bundle directory: {ROOT_PATH / 'dist' / 'AIOrchestrator'}")
        else:
            print(f"Executable: {ROOT_PATH / 'dist' / 'AIOrchestrator.exe'}")
        return

    print("\nBuild failed!")
    sys.exit(1)


def build_dev() -> None:
    """Run a development desktop build."""
    print("Running development build...")
    build_exe(debug=True, onefile=False, target="main.py")


def build_release() -> None:
    """Run the release desktop build."""
    print("Running release build...")
    sync_version_metadata(ReleaseChannel.STABLE)
    build_exe(debug=False, onefile=True, target=None)


def render_installer_script(version: str) -> Path:
    """Render the Inno Setup script with current metadata."""
    template_path = ROOT_PATH / "installer" / "windows_setup.iss"
    if not template_path.exists():
        raise FileNotFoundError(f"Installer template not found: {template_path}")

    output_dir = ROOT_PATH / "dist" / "installer"
    output_dir.mkdir(parents=True, exist_ok=True)
    script_path = output_dir / "AIOrchestrator.iss"
    replacements = {
        "__APP_VERSION__": version,
        "__APP_EXE__": str((ROOT_PATH / "dist" / "AIOrchestrator.exe").resolve()).replace("\\", "\\\\"),
        "__APP_ICON__": str((ROOT_PATH / "assets" / "icon.ico").resolve()).replace("\\", "\\\\"),
        "__OUTPUT_DIR__": str(output_dir.resolve()).replace("\\", "\\\\"),
        "__SOURCE_ROOT__": str(ROOT_PATH.resolve()).replace("\\", "\\\\"),
        "__BUILD_COMMIT__": get_git_commit_hash() or "unknown",
    }

    content = template_path.read_text(encoding="utf-8")
    for marker, value in replacements.items():
        content = content.replace(marker, value)
    script_path.write_text(content, encoding="utf-8")
    print(f"Installer script generated: {script_path}")
    return script_path


def locate_iscc() -> str | None:
    """Locate the Inno Setup compiler."""
    candidates = [
        shutil.which("ISCC"),
        shutil.which("ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def build_installer() -> Path:
    """Build the Windows installer when Inno Setup is available."""
    version = get_version()
    exe_path = ROOT_PATH / "dist" / "AIOrchestrator.exe"
    if not exe_path.exists():
        raise FileNotFoundError(f"Executable not found for installer build: {exe_path}")

    script_path = render_installer_script(version)
    iscc = locate_iscc()
    if not iscc:
        print("Inno Setup compiler not found. Installer script generated but not compiled.")
        return script_path

    result = run_logged_command([iscc, str(script_path)], "installer")
    if result.returncode != 0:
        raise RuntimeError("Installer compilation failed")
    return script_path


def run_tests() -> bool:
    """Run the test suite."""
    print("Running tests...")
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=short"],
        cwd=ROOT_PATH,
        env=env,
    )
    return result.returncode == 0


def lint() -> bool:
    """Run linting checks."""
    print("Running linting...")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=ROOT_PATH,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("Linting passed!")
        return True

    print("Linting issues found:")
    print(result.stdout)
    return False


def create_release(tag: str) -> None:
    """Create release artifacts in dist/releases/."""
    version = get_version()
    release_dir = get_release_dir(version)

    portable_exe = ROOT_PATH / "dist" / "AIOrchestrator.exe"
    if portable_exe.exists():
        shutil.copy(portable_exe, release_dir / f"AIOrchestrator-{version}-win64.exe")

    installer_exe = ROOT_PATH / "dist" / "installer" / f"AI-Orchestrator-Setup-{version}.exe"
    if installer_exe.exists():
        shutil.copy(installer_exe, release_dir / installer_exe.name)

    for filename in ["CHANGELOG.md", "README.md", "update_config.json", "version.json"]:
        source = ROOT_PATH / filename
        if source.exists():
            shutil.copy(source, release_dir / source.name)

    manifest = {
        "version": version,
        "tag": tag or f"v{version}",
        "build_date": datetime.now().isoformat(timespec="seconds"),
        "commit_hash": get_git_commit_hash(),
        "release_url": UpdateConfig.load(ROOT_PATH).release_url,
        "artifacts": sorted(path.name for path in release_dir.iterdir()),
    }
    (release_dir / "release_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    notes = f"""# AI Orchestrator v{version}

## Release Date
{datetime.now().strftime("%Y-%m-%d")}

## Changes
{get_recent_changelog_markdown(ROOT_PATH, max_entries=1)}

## Installation
1. Download `AI-Orchestrator-Setup-{version}.exe`
2. Run the installer
3. Open AI Orchestrator from the Start Menu or desktop shortcut

## Portable Artifact
- `AIOrchestrator-{version}-win64.exe`

## Requirements
- Windows 10/11 (64-bit)
- 4GB RAM minimum

## Checksums
```
SHA256: [Calculate and add]
```
"""
    (release_dir / "RELEASE_NOTES.md").write_text(notes, encoding="utf-8")
    print(f"Release package created: {release_dir}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AI Orchestrator Build Script")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    subparsers.add_parser("clean", help="Clean build artifacts")

    build_parser = subparsers.add_parser("build", help="Build executable")
    build_parser.add_argument("--debug", action="store_true", help="Debug build")
    build_parser.add_argument("--onedir", action="store_true", help="Build as directory instead of single file")
    build_parser.add_argument("--target", help="PyInstaller target (.spec or .py). Defaults to ai_orchestrator.spec when present")

    subparsers.add_parser("build-dev", help="Run a development desktop build")
    subparsers.add_parser("build-release", help="Run the release desktop build")
    subparsers.add_parser("installer", help="Generate the Windows installer")
    subparsers.add_parser("test", help="Run tests")
    subparsers.add_parser("lint", help="Run linting")

    release_parser = subparsers.add_parser("release", help="Create release package")
    release_parser.add_argument("--tag", default="", help="Git tag for release")

    version_parser = subparsers.add_parser("version", help="Version operations")
    version_parser.add_argument("--bump", choices=["major", "minor", "patch"], help="Bump version")
    version_parser.add_argument("--set", dest="set_version", help="Set specific version")

    subparsers.add_parser("all", help="Run tests, lint, and build")

    args = parser.parse_args()

    if args.command == "clean":
        clean()
    elif args.command == "build":
        build_exe(debug=args.debug, onefile=not args.onedir, target=args.target)
    elif args.command == "build-dev":
        build_dev()
    elif args.command == "build-release":
        build_release()
    elif args.command == "installer":
        try:
            build_installer()
        except Exception as exc:
            print(exc)
            sys.exit(1)
    elif args.command == "test":
        if not run_tests():
            sys.exit(1)
    elif args.command == "lint":
        if not lint():
            sys.exit(1)
    elif args.command == "release":
        build_release()
        try:
            build_installer()
        except Exception as exc:
            print(f"Installer step skipped or failed: {exc}")
        create_release(args.tag)
    elif args.command == "version":
        manager = get_version_manager(ROOT_PATH)
        if args.bump:
            new_version = manager.bump(args.bump)
            print(f"Version bumped to: {new_version}")
        elif args.set_version:
            new_version = manager.set_version(args.set_version)
            print(f"Version set to: {new_version}")
        else:
            print(f"Current version: {get_version()}")
    elif args.command == "all":
        if not run_tests():
            print("Tests failed, aborting build")
            sys.exit(1)
        if not lint():
            print("Linting failed, continuing with build...")
        build_release()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
