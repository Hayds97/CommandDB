@echo off
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\CommandDBQuickAdd.lnk"

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo [SUCCESS] Service removed from startup.
) else (
    echo [INFO] Service was not found in startup.
)
pause