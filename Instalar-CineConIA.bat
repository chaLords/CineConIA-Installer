@echo off
setlocal enabledelayedexpansion
cd /D "%~dp0"
title Instalador de Cine con IA
chcp 65001 >nul

:: Este archivo hace lo minimo imprescindible: conseguir un Python y ceder
:: el paso. Todo lo que se pueda decidir, explicar o deshacer vive en
:: Python, donde se lee y se prueba. Un instalador que toma decisiones
:: dentro de un .bat acaba siendo imposible de mantener.

set "DESTINO=%~dp0ComfyUI"
set "PY=%DESTINO%\python_embeded\python.exe"

echo.
echo   ============================================================
echo     Cine con IA  ·  instalador de ComfyUI
echo     https://www.youtube.com/@cineconia.oficial
echo   ============================================================
echo.

:: --- Si ya hay un ComfyUI aqui, se salta la descarga -------------------
if exist "%PY%" (
    echo   ComfyUI ya esta en esta carpeta. Abriendo el menu...
    echo.
    "%PY%" -s "%~dp0src\instalador.py" "%DESTINO%"
    goto :fin
)

:: --- Comprobaciones antes de descargar 2 GB ----------------------------
where curl.exe >nul 2>&1 || (
    echo   [X] Falta curl.exe. Necesitas Windows 10 version 1803 o superior.
    goto :fin
)

echo   No hay ComfyUI en esta carpeta. Hay que descargarlo.
echo.

:: Que portable toca segun la grafica. ComfyUI publica uno por fabricante,
:: asi que aqui se cubren las tres y no solo NVIDIA.
set "VARIANTE=nvidia"
where nvidia-smi.exe >nul 2>&1 && (
    for /f "tokens=*" %%g in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do set "GPU=%%g"
)
if defined GPU (
    echo   GPU detectada: !GPU!
) else (
    echo   No se detecto una GPU NVIDIA.
    echo.
    echo     1^) AMD        2^) Intel        3^) NVIDIA de todos modos
    set /p "OPCION=   Elige [1-3]: "
    if "!OPCION!"=="1" set "VARIANTE=amd"
    if "!OPCION!"=="2" set "VARIANTE=intel"
)
echo   Version portable: !VARIANTE!
echo.

:: --- 7zr.exe, que Windows no sabe abrir .7z por su cuenta --------------
if not exist "7zr.exe" (
    echo   Descargando el extractor de 7-Zip...
    curl -L -s -o "7zr.exe" "https://www.7-zip.org/a/7zr.exe" || (
        echo   [X] No se pudo descargar 7zr.exe
        goto :fin
    )
)

:: --- El portable oficial ------------------------------------------------
set "PAQUETE=ComfyUI_windows_portable_!VARIANTE!.7z"
if not exist "%PAQUETE%" (
    echo   Descargando ComfyUI ^(unos 2 GB, puede tardar^)...
    curl -L --retry 3 --progress-bar -o "%PAQUETE%" ^
      "https://github.com/Comfy-Org/ComfyUI/releases/latest/download/%PAQUETE%" || (
        echo   [X] Fallo la descarga.
        goto :fin
    )
)

echo   Extrayendo...
"7zr.exe" x "%PAQUETE%" -o"%~dp0" -y >nul || (
    echo   [X] Fallo la extraccion.
    goto :fin
)

:: El portable se descomprime como ComfyUI_windows_portable
if exist "%~dp0ComfyUI_windows_portable\python_embeded\python.exe" (
    if not exist "%DESTINO%" ren "ComfyUI_windows_portable" "ComfyUI"
)

if not exist "%PY%" (
    echo   [X] No encuentro python_embeded tras extraer.
    goto :fin
)

echo.
echo   ComfyUI instalado. Abriendo el menu...
echo.
"%PY%" -s "%~dp0src\instalador.py" "%DESTINO%"

:fin
echo.
echo   Pulsa una tecla para salir...
pause >nul
