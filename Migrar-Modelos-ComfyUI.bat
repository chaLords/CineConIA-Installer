@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /D "%~dp0"
title Migrar modelos de ComfyUI
chcp 65001 >nul

set "SCRIPT=%~dp0src\migrar_modelos.py"
set "PYEXE="
set "PYARGS="

echo.
echo   ============================================================
echo     Migrador seguro de modelos de ComfyUI
echo   ============================================================
echo.
echo   Cierra ComfyUI antes de comenzar.
echo   El script SIEMPRE muestra una simulacion antes de copiar o mover.
echo.

if not exist "%SCRIPT%" (
    echo   [X] No encuentro src\migrar_modelos.py
    goto :fin
)

if exist "%~dp0ComfyUI\python_embeded\python.exe" (
    set "PYEXE=%~dp0ComfyUI\python_embeded\python.exe"
    goto :ejecutar
)

where py.exe >nul 2>&1 && (
    set "PYEXE=py.exe"
    set "PYARGS=-3"
    goto :ejecutar
)

where python.exe >nul 2>&1 && (
    set "PYEXE=python.exe"
    goto :ejecutar
)

echo   No encontre Python en este equipo.
echo   Puedes usar el Python embebido de cualquier ComfyUI portable existente.
echo.
echo   Selecciona la carpeta RAIZ del ComfyUI portable.
echo   Debe contener python_embeded\python.exe
echo.

set "PORTABLE="
for /f "delims=" %%I in ('powershell -NoProfile -Sta -Command "$s=New-Object -ComObject Shell.Application; $f=$s.BrowseForFolder(0,''Selecciona la carpeta raiz de ComfyUI portable'',0,0); if($f){$f.Self.Path}"') do set "PORTABLE=%%I"

if not defined PORTABLE (
    echo   [X] No se selecciono ninguna carpeta.
    goto :fin
)

if exist "!PORTABLE!\python_embeded\python.exe" (
    set "PYEXE=!PORTABLE!\python_embeded\python.exe"
    goto :ejecutar
)

if exist "!PORTABLE!\ComfyUI\python_embeded\python.exe" (
    set "PYEXE=!PORTABLE!\ComfyUI\python_embeded\python.exe"
    goto :ejecutar
)

echo   [X] Esa carpeta no contiene python_embeded\python.exe
goto :fin

:ejecutar
echo   Python: !PYEXE!
echo.
"!PYEXE!" !PYARGS! -s "%SCRIPT%"
set "RC=!errorlevel!"
if not "!RC!"=="0" (
    echo.
    echo   [X] El migrador termino con codigo !RC!.
)

:fin
echo.
echo   Pulsa una tecla para salir...
pause >nul
