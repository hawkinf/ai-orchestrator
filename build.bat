@echo off
REM Build script for AI Orchestrator on Windows
REM Usage: build.bat [command]
REM Commands: clean, build, test, lint, release, all

setlocal enabledelayedexpansion

cd /d "%~dp0"

if "%1"=="" (
    echo AI Orchestrator Build Script
    echo.
    echo Usage: build.bat [command]
    echo.
    echo Commands:
    echo   clean    - Clean build artifacts
    echo   build    - Build executable
    echo   test     - Run tests
    echo   lint     - Run linting
    echo   release  - Create release package
    echo   all      - Run tests, lint, and build
    echo   version  - Show current version
    echo.
    exit /b 0
)

if "%1"=="clean" (
    echo Cleaning build artifacts...
    if exist build rmdir /s /q build
    if exist dist rmdir /s /q dist
    echo Clean complete!
    exit /b 0
)

if "%1"=="build" (
    echo Building AI Orchestrator...
    python build.py build
    exit /b !errorlevel!
)

if "%1"=="test" (
    echo Running tests...
    python -m pytest -v --tb=short
    exit /b !errorlevel!
)

if "%1"=="lint" (
    echo Running linting...
    python -m ruff check .
    exit /b !errorlevel!
)

if "%1"=="release" (
    echo Creating release...
    python build.py release
    exit /b !errorlevel!
)

if "%1"=="all" (
    echo Running full build pipeline...
    python build.py all
    exit /b !errorlevel!
)

if "%1"=="version" (
    python -c "from orchestrator.version import get_version; print(f'Version: {get_version()}')"
    exit /b 0
)

echo Unknown command: %1
echo Run 'build.bat' without arguments for help.
exit /b 1
