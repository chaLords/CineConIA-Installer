@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -Sta -ExecutionPolicy Bypass -File "%~dp0src\bootstrap.ps1" %*
set "RC=%errorlevel%"
echo.
pause
exit /b %RC%
