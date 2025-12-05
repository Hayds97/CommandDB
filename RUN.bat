@echo off
:: Set current directory to the folder where this file is
cd /d "%~dp0"

:: Run the Smart Launcher using Python 3.12
py -3.12 src\launcher.py

:: If the launcher crashes, keep window open so we can see why
if %errorlevel% neq 0 pause