#!/usr/bin/env python3
"""Build script for AI Orchestrator desktop application."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT_PATH = Path(__file__).parent


def get_version() -> str:
    """Get current version from version.json."""
    version_file = ROOT_PATH / "version.json"
    if version_file.exists():
        with open(version_file) as f:
            data = json.load(f)
        return data.get("version", "0.1.0")
    return "0.1.0"


def update_version_info():
    """Update version_info.txt with current version."""
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
            StringStruct('FileDescription', 'AI Orchestrator - Local Development Assistant'),
            StringStruct('FileVersion', '{version}'),
            StringStruct('InternalName', 'AIOrchestrator'),
            StringStruct('LegalCopyright', '© {datetime.now().year} Hawk Informatica. All rights reserved.'),
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
    with open(ROOT_PATH / "version_info.txt", "w") as f:
        f.write(content)

    print(f"Updated version_info.txt to version {version}")


def clean():
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


def build_exe(debug: bool = False, onefile: bool = True):
    """Build the executable using PyInstaller."""
    print(f"Building AI Orchestrator v{get_version()}...")

    # Update version info
    update_version_info()

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
    ]

    if debug:
        cmd.append("--debug=all")

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # Use spec file
    spec_file = ROOT_PATH / "ai_orchestrator.spec"
    if spec_file.exists():
        cmd.append(str(spec_file))
    else:
        # Fallback to direct options
        cmd.extend([
            "--name=AIOrchestrator",
            "--windowed",
            f"--add-data={ROOT_PATH / 'version.json'};.",
            f"--version-file={ROOT_PATH / 'version_info.txt'}",
            str(ROOT_PATH / "main.py"),
        ])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT_PATH)

    if result.returncode == 0:
        print("\nBuild successful!")
        print(f"Executable: {ROOT_PATH / 'dist' / 'AIOrchestrator.exe'}")
    else:
        print("\nBuild failed!")
        sys.exit(1)


def run_tests():
    """Run the test suite."""
    print("Running tests...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=short"],
        cwd=ROOT_PATH,
    )
    return result.returncode == 0


def lint():
    """Run linting checks."""
    print("Running linting...")

    # Run ruff if available
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=ROOT_PATH,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("Linting passed!")
        return True
    else:
        print("Linting issues found:")
        print(result.stdout)
        return False


def create_release(tag: str):
    """Create a release package."""
    version = get_version()
    release_dir = ROOT_PATH / "releases" / f"v{version}"
    release_dir.mkdir(parents=True, exist_ok=True)

    # Copy executable
    exe_path = ROOT_PATH / "dist" / "AIOrchestrator.exe"
    if exe_path.exists():
        shutil.copy(exe_path, release_dir / f"AIOrchestrator-{version}-win64.exe")

    # Create release notes template
    notes_file = release_dir / "RELEASE_NOTES.md"
    with open(notes_file, "w") as f:
        f.write(f"""# AI Orchestrator v{version}

## Release Date
{datetime.now().strftime("%Y-%m-%d")}

## Changes
- [Add changes here]

## Installation
1. Download `AIOrchestrator-{version}-win64.exe`
2. Run the executable
3. Follow the setup wizard

## Requirements
- Windows 10/11 (64-bit)
- 4GB RAM minimum

## Checksums
```
SHA256: [Calculate and add]
```
""")

    print(f"Release package created: {release_dir}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AI Orchestrator Build Script")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Clean command
    subparsers.add_parser("clean", help="Clean build artifacts")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build executable")
    build_parser.add_argument("--debug", action="store_true", help="Debug build")
    build_parser.add_argument("--onedir", action="store_true", help="Build as directory instead of single file")

    # Test command
    subparsers.add_parser("test", help="Run tests")

    # Lint command
    subparsers.add_parser("lint", help="Run linting")

    # Release command
    release_parser = subparsers.add_parser("release", help="Create release package")
    release_parser.add_argument("--tag", default="", help="Git tag for release")

    # Version command
    version_parser = subparsers.add_parser("version", help="Version operations")
    version_parser.add_argument("--bump", choices=["major", "minor", "patch"], help="Bump version")
    version_parser.add_argument("--set", dest="set_version", help="Set specific version")

    # All command (test + lint + build)
    subparsers.add_parser("all", help="Run tests, lint, and build")

    args = parser.parse_args()

    if args.command == "clean":
        clean()
    elif args.command == "build":
        build_exe(debug=args.debug, onefile=not args.onedir)
    elif args.command == "test":
        if not run_tests():
            sys.exit(1)
    elif args.command == "lint":
        if not lint():
            sys.exit(1)
    elif args.command == "release":
        build_exe()
        create_release(args.tag)
    elif args.command == "version":
        if args.bump:
            from orchestrator.version import get_version_manager
            manager = get_version_manager(ROOT_PATH)
            new_version = manager.bump(args.bump)
            print(f"Version bumped to: {new_version}")
        elif args.set_version:
            from orchestrator.version import get_version_manager
            manager = get_version_manager(ROOT_PATH)
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
        build_exe()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
