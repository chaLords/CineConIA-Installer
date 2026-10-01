@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0ComfyUI-Setup.bat" --advanced %*
exit /b %errorlevel%
