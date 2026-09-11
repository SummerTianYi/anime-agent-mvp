@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-mvp.ps1" %*
set "startup_exit=%errorlevel%"
if not "%startup_exit%"=="0" (
    echo.
    echo Anime Agent startup failed. Keep this window open and report the error above.
    pause
)
exit /b %startup_exit%
