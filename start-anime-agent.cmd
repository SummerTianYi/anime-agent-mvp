@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-mvp.ps1"
if errorlevel 1 (
    echo.
    echo Anime Agent startup failed. Keep this window open and report the error above.
    pause
)
endlocal
