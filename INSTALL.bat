@echo off
cd /d "%~dp0"
title CommandDB Installer

echo Checking for Python 3.12...
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.12 is required. Please install it from python.org.
    pause
    exit /b
)

echo Launching Installer...
py -3.12 src/installer.py