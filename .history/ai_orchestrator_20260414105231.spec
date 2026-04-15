# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for AI Orchestrator."""

from pathlib import Path

block_cipher = None

# Get the root path
ROOT_PATH = Path(SPECPATH)

# Collect data files
# NOTE: Only include files/folders that actually exist
# - version.json: App version metadata (required)
# - config.yaml: Default configuration (required)
# - prompts/: LLM prompt templates (required for planner/reviewer)
datas = [
    # Version file - required for app version display
    (str(ROOT_PATH / "version.json"), "."),
    # Update config and changelog - required for product release UX
    (str(ROOT_PATH / "update_config.json"), "."),
    (str(ROOT_PATH / "CHANGELOG.md"), "."),
    # Configuration file - required for app settings
    (str(ROOT_PATH / "config.yaml"), "."),
    # Prompt templates - required for LLM interactions
    (str(ROOT_PATH / "prompts"), "prompts"),
]

# Hidden imports for dynamic modules
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "pydantic",
    "pydantic_settings",
    "openai",
    "httpx",
    "httpcore",
    "anyio",
    "sniffio",
    "certifi",
    "charset_normalizer",
    "idna",
    "urllib3",
]


def resolve_version_resource() -> str | None:
    """Return a safe version resource path or disable it if invalid."""
    version_file = ROOT_PATH / "version_info.txt"
    if not version_file.exists():
        print(f"[ai_orchestrator.spec] version resource not found: {version_file}")
        return None

    try:
        text = version_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"[ai_orchestrator.spec] version resource is not valid UTF-8: {version_file}")
        return None

    if any(ord(char) > 127 for char in text):
        print(f"[ai_orchestrator.spec] version resource contains non-ASCII characters, disabling version metadata: {version_file}")
        return None

    return str(version_file)

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
    version=resolve_version_resource(),
)
