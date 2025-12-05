@echo off
cd /d "%~dp0\.."

set "PYTHONW=.venv\Scripts\pythonw.exe"

if exist "%PYTHONW%" (
	start "CommandDBQuickAdd" "%PYTHONW%" src\quick_add.py
) else (
	echo [.venv not found] Launching fallback via py -3.12
	py -3.12 src\launcher.py
)