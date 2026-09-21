@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /D "%~dp0"
title Instalador adaptativo de ComfyUI
chcp 65001 >nul

set "DESTINO=%~dp0ComfyUI"
set "PY=%DESTINO%\python_embeded\python.exe"
set "MAIN=%DESTINO%\ComfyUI\main.py"
set "FABRICANTE="
set "GPU="
set "VARIANTE="
set "PAQUETE="
set "MIN_ESPACIO_GB=8"

echo.
echo   ============================================================
echo     ComfyUI - instalador adaptativo de Cine con IA
echo   ============================================================
echo.

if exist "%PY%" if exist "%MAIN%" (
    echo   ComfyUI ya esta instalado. Analizando el entorno real...
    "%PY%" -s "%~dp0src\instalador.py" "%DESTINO%"
    goto :fin
)

where curl.exe >nul 2>&1 || (
    echo   [X] Falta curl.exe. Se necesita Windows 10 1803 o superior.
    goto :fin
)
where powershell.exe >nul 2>&1 || (
    echo   [X] No se encuentra PowerShell.
    goto :fin
)

for /f %%G in ('powershell -NoProfile -Command "[math]::Round((Get-PSDrive -Name ([IO.Path]::GetPathRoot('%~dp0').Substring(0,1))).Free/1GB,1)"') do set "ESPACIO=%%G"
if defined ESPACIO (
    echo   Espacio libre: !ESPACIO! GB
    powershell -NoProfile -Command "if ([double]'!ESPACIO!' -lt %MIN_ESPACIO_GB%) { exit 1 } else { exit 0 }"
    if errorlevel 1 (
        echo   [X] Hay menos de %MIN_ESPACIO_GB% GB libres.
        goto :fin
    )
)

where nvidia-smi.exe >nul 2>&1 && (
    for /f "tokens=* usebackq" %%G in (`nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul`) do (
        if not defined GPU set "GPU=%%G"
    )
    if defined GPU set "FABRICANTE=nvidia"
)

if not defined FABRICANTE (
    for /f "usebackq delims=" %%G in (`powershell -NoProfile -Command "$n=(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue ^| Select-Object -ExpandProperty Name); $n -join ' ^| '"`) do set "GPU=%%G"
    echo(!GPU! | findstr /I /C:"NVIDIA" >nul && set "FABRICANTE=nvidia"
    if not defined FABRICANTE echo(!GPU! | findstr /I /C:"AMD" /C:"Radeon" >nul && set "FABRICANTE=amd"
    if not defined FABRICANTE echo(!GPU! | findstr /I /C:"Intel" /C:"Arc" >nul && set "FABRICANTE=intel"
)

if not defined FABRICANTE (
    echo   No pude identificar automaticamente el fabricante de la GPU.
    echo     1^) NVIDIA
    echo     2^) AMD
    echo     3^) Intel
    set /p "OPCION=   Elige [1-3]: "
    if "!OPCION!"=="1" set "FABRICANTE=nvidia"
    if "!OPCION!"=="2" set "FABRICANTE=amd"
    if "!OPCION!"=="3" set "FABRICANTE=intel"
)
if not defined FABRICANTE (
    echo   [X] No se eligio una GPU compatible.
    goto :fin
)

echo   GPU detectada: !GPU!
echo   Fabricante:     !FABRICANTE!

if /I "!FABRICANTE!"=="nvidia" (
    set "VARIANTE=nvidia"
    set "NV_MAJOR=0"
    where nvidia-smi.exe >nul 2>&1 && (
        for /f "tokens=1 delims=." %%V in ('nvidia-smi --query-gpu^=driver_version --format^=csv^,noheader 2^>nul') do (
            if "!NV_MAJOR!"=="0" set "NV_MAJOR=%%V"
        )
    )
    set "LEGACY=0"
    echo(!GPU! | findstr /I /C:"GTX 10" /C:"TITAN Xp" /C:"Quadro P" /C:"Tesla P" >nul && set "LEGACY=1"
    if not "!NV_MAJOR!"=="0" if !NV_MAJOR! LSS 580 set "LEGACY=1"
    if "!LEGACY!"=="1" set "VARIANTE=nvidia_cu126"
)
if /I "!FABRICANTE!"=="amd" set "VARIANTE=amd"
if /I "!FABRICANTE!"=="intel" set "VARIANTE=intel"

set "PAQUETE=ComfyUI_windows_portable_!VARIANTE!.7z"
echo   Portable:       !PAQUETE!
echo.

if not exist "7zr.exe" (
    echo   Descargando extractor 7-Zip...
    if exist "7zr.exe.part" del /Q "7zr.exe.part" >nul 2>&1
    curl.exe --fail --location --retry 5 --retry-delay 2 --progress-bar -o "7zr.exe.part" "https://www.7-zip.org/a/7zr.exe"
    if errorlevel 1 (
        del /Q "7zr.exe.part" >nul 2>&1
        echo   [X] No se pudo descargar 7zr.exe.
        goto :fin
    )
    move /Y "7zr.exe.part" "7zr.exe" >nul
)
"7zr.exe" i >nul 2>&1
if errorlevel 1 (
    echo   [X] 7zr.exe no parece ejecutable.
    goto :fin
)

if exist "!PAQUETE!" (
    call :VERIFICAR_HASH "!PAQUETE!"
    if errorlevel 1 (
        echo   El paquete existente no paso la verificacion; se descargara otra vez.
        del /Q "!PAQUETE!" >nul 2>&1
    )
)

if not exist "!PAQUETE!" (
    echo   Descargando ComfyUI...
    if exist "!PAQUETE!.part" del /Q "!PAQUETE!.part" >nul 2>&1
    curl.exe --fail --location --retry 5 --retry-delay 2 --progress-bar -o "!PAQUETE!.part" "https://github.com/Comfy-Org/ComfyUI/releases/latest/download/!PAQUETE!"
    if errorlevel 1 (
        del /Q "!PAQUETE!.part" >nul 2>&1
        echo   [X] Fallo la descarga de ComfyUI.
        goto :fin
    )
    move /Y "!PAQUETE!.part" "!PAQUETE!" >nul
    call :VERIFICAR_HASH "!PAQUETE!"
    if errorlevel 1 (
        echo   [X] El SHA-256 no coincide con el publicado por Comfy-Org.
        del /Q "!PAQUETE!" >nul 2>&1
        goto :fin
    )
)

if exist "%DESTINO%" if not exist "%PY%" (
    echo.
    echo   Se encontro una carpeta ComfyUI incompleta.
    set /p "REPARAR=   Guardarla como copia y reinstalar? [S/n]: "
    if /I "!REPARAR!"=="N" goto :fin
    for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "MARCA=%%T"
    ren "%DESTINO%" "ComfyUI_incompleto_!MARCA!"
)

echo   Extrayendo...
if exist "%~dp0ComfyUI_windows_portable" rmdir /S /Q "%~dp0ComfyUI_windows_portable"
"7zr.exe" x "!PAQUETE!" -o"%~dp0" -y >nul
if errorlevel 1 (
    echo   [X] Fallo la extraccion.
    goto :fin
)
if exist "%~dp0ComfyUI_windows_portable\python_embeded\python.exe" (
    if not exist "%DESTINO%" ren "%~dp0ComfyUI_windows_portable" "ComfyUI"
)
if not exist "%PY%" (
    echo   [X] No encuentro python_embeded despues de extraer.
    goto :fin
)
if not exist "%MAIN%" (
    echo   [X] La instalacion no contiene ComfyUI\main.py.
    goto :fin
)

echo.
echo   ComfyUI base instalado. Analizando PyTorch y aceleradores reales...
"%PY%" -s "%~dp0src\instalador.py" "%DESTINO%" "!FABRICANTE!" "!VARIANTE!"
goto :fin

:VERIFICAR_HASH
set "DIGEST="
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $r=Invoke-RestMethod -Headers @{'User-Agent'='CineConIA-Installer'} 'https://api.github.com/repos/Comfy-Org/ComfyUI/releases/latest'; $a=$r.assets ^| Where-Object name -eq '%~1'; if($a.digest){$a.digest}" 2^>nul`) do set "DIGEST=%%H"
if not defined DIGEST (
    echo   [!] GitHub no entrego digest; se validara el archivo con 7-Zip.
    "7zr.exe" t "%~1" >nul 2>&1
    exit /b !errorlevel!
)
set "ESPERADO=!DIGEST:sha256:=!"
set "REAL="
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath '%~1').Hash.ToLower()"`) do set "REAL=%%H"
if /I "!REAL!"=="!ESPERADO!" (
    echo   SHA-256 verificado.
    exit /b 0
)
exit /b 1

:fin
echo.
echo   Pulsa una tecla para salir...
pause >nul
