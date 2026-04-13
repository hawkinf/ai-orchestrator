# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for AI Orchestrator."""

import sys
from pathlib import Path

block_cipher = None

# Get the root path
ROOT_PATH = Path(SPECPATH)

# Collect data files
datas = [
    # Version file
    (str(ROOT_PATH / "version.json"), "."),
    # Config templates
    (str(ROOT_PATH / "config"), "config"),
]

# Hidden imports for dynamic modules
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "pydantic",
    "pydantic_settings",
    "openai",
    "anthropic",
    "httpx",
    "httpcore",
    "anyio",
    "sniffio",
    "certifi",
    "charset_normalizer",
    "idna",
    "urllib3",
]

a = Analysis(
    [str(ROOT_PATH / "main.py")],
    pathex=[str(ROOT_PATH)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "PIL",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AIOrchestrator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT_PATH / "assets" / "icon.ico") if (ROOT_PATH / "assets" / "icon.ico").exists() else None,
    version=str(ROOT_PATH / "version_info.txt") if (ROOT_PATH / "version_info.txt").exists() else None,
)
