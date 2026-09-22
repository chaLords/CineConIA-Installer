@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /D "%~dp0"
chcp 65001 >nul
call :SELECT_LANGUAGE "%~1"
set "MIN_ESPACIO_GB=8"
call :LOAD_TEXT
title !T_TITLE!
set "DESTINO=%~dp0ComfyUI"
set "PY=%DESTINO%\python_embeded\python.exe"
set "MAIN=%DESTINO%\ComfyUI\main.py"
set "FABRICANTE="
set "GPU="
set "VARIANTE="
set "PAQUETE="
echo.
echo   ============================================================
echo     !T_BANNER!
echo   ============================================================
echo.
if exist "%PY%" if exist "%MAIN%" (
    echo   !T_ALREADY!
    "%PY%" -s "%~dp0src\instalador.py" "%DESTINO%"
    goto :fin
)
where curl.exe >nul 2>&1 || (echo   [X] !T_NO_CURL!&goto :fin)
where powershell.exe >nul 2>&1 || (echo   [X] !T_NO_PS!&goto :fin)
for /f %%G in ('powershell -NoProfile -Command "[math]::Round((Get-PSDrive -Name ([IO.Path]::GetPathRoot('%~dp0').Substring(0,1))).Free/1GB,1)"') do set "ESPACIO=%%G"
if defined ESPACIO (
    echo   !T_FREE!: !ESPACIO! GB
    powershell -NoProfile -Command "if ([double]'!ESPACIO!' -lt %MIN_ESPACIO_GB%) { exit 1 } else { exit 0 }"
    if errorlevel 1 (echo   [X] !T_LOW_SPACE!&goto :fin)
)
where nvidia-smi.exe >nul 2>&1 && (
    for /f "tokens=*" %%G in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do if not defined GPU set "GPU=%%G"
    if defined GPU set "FABRICANTE=nvidia"
)
if not defined FABRICANTE (
    for /f "delims=" %%G in ('powershell -NoProfile -Command "$n=(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue ^| Select-Object -ExpandProperty Name); $n -join ' ^| '"') do set "GPU=%%G"
    echo(!GPU! | findstr /I /C:"NVIDIA" >nul && set "FABRICANTE=nvidia"
    if not defined FABRICANTE echo(!GPU! | findstr /I /C:"AMD" /C:"Radeon" >nul && set "FABRICANTE=amd"
    if not defined FABRICANTE echo(!GPU! | findstr /I /C:"Intel" /C:"Arc" >nul && set "FABRICANTE=intel"
)
if not defined FABRICANTE (
    echo   !T_GPU_UNKNOWN!
    echo     1^) NVIDIA
    echo     2^) AMD
    echo     3^) Intel
    set /p "OPCION=   !T_CHOOSE_GPU! [1-3]: "
    if "!OPCION!"=="1" set "FABRICANTE=nvidia"
    if "!OPCION!"=="2" set "FABRICANTE=amd"
    if "!OPCION!"=="3" set "FABRICANTE=intel"
)
if not defined FABRICANTE (echo   [X] !T_GPU_NONE!&goto :fin)
echo   !T_GPU!: !GPU!
echo   !T_VENDOR!: !FABRICANTE!
if /I "!FABRICANTE!"=="nvidia" (
    set "VARIANTE=nvidia"
    set "NV_MAJOR=0"
    where nvidia-smi.exe >nul 2>&1 && (
        for /f "tokens=1 delims=." %%V in ('nvidia-smi --query-gpu^=driver_version --format^=csv^,noheader 2^>nul') do if "!NV_MAJOR!"=="0" set "NV_MAJOR=%%V"
    )
    set "LEGACY=0"
    echo(!GPU! | findstr /I /C:"GTX 10" /C:"TITAN Xp" /C:"Quadro P" /C:"Tesla P" >nul && set "LEGACY=1"
    if not "!NV_MAJOR!"=="0" if !NV_MAJOR! LSS 580 set "LEGACY=1"
    if "!LEGACY!"=="1" set "VARIANTE=nvidia_cu126"
)
if /I "!FABRICANTE!"=="amd" set "VARIANTE=amd"
if /I "!FABRICANTE!"=="intel" set "VARIANTE=intel"
set "PAQUETE=ComfyUI_windows_portable_!VARIANTE!.7z"
echo   !T_PORTABLE!: !PAQUETE!
echo.
if not exist "7zr.exe" (
    echo   !T_DOWNLOAD_7Z!
    if exist "7zr.exe.part" del /Q "7zr.exe.part" >nul 2>&1
    curl.exe --fail --location --retry 5 --retry-delay 2 --progress-bar -o "7zr.exe.part" "https://www.7-zip.org/a/7zr.exe"
    if errorlevel 1 (del /Q "7zr.exe.part" >nul 2>&1&echo   [X] !T_DOWNLOAD_7Z_FAIL!&goto :fin)
    move /Y "7zr.exe.part" "7zr.exe" >nul
)
"7zr.exe" i >nul 2>&1
if errorlevel 1 (echo   [X] !T_7Z_BAD!&goto :fin)
if exist "!PAQUETE!" (
    call :VERIFICAR_HASH "!PAQUETE!"
    if errorlevel 1 (echo   !T_EXISTING_BAD!&del /Q "!PAQUETE!" >nul 2>&1)
)
if not exist "!PAQUETE!" (
    echo   !T_DOWNLOAD_COMFY!
    if exist "!PAQUETE!.part" del /Q "!PAQUETE!.part" >nul 2>&1
    curl.exe --fail --location --retry 5 --retry-delay 2 --progress-bar -o "!PAQUETE!.part" "https://github.com/Comfy-Org/ComfyUI/releases/latest/download/!PAQUETE!"
    if errorlevel 1 (del /Q "!PAQUETE!.part" >nul 2>&1&echo   [X] !T_DOWNLOAD_COMFY_FAIL!&goto :fin)
    move /Y "!PAQUETE!.part" "!PAQUETE!" >nul
    call :VERIFICAR_HASH "!PAQUETE!"
    if errorlevel 1 (echo   [X] !T_HASH_FAIL!&del /Q "!PAQUETE!" >nul 2>&1&goto :fin)
)
if exist "%DESTINO%" if not exist "%PY%" (
    echo.
    echo   !T_INCOMPLETE!
    set /p "REPARAR=   !T_BACKUP_REINSTALL! "
    if /I "!REPARAR!"=="N" goto :fin
    if /I "!REPARAR!"=="NO" goto :fin
    for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "MARCA=%%T"
    ren "%DESTINO%" "ComfyUI_incompleto_!MARCA!"
)
echo   !T_EXTRACTING!
if exist "%~dp0ComfyUI_windows_portable" rmdir /S /Q "%~dp0ComfyUI_windows_portable"
"7zr.exe" x "!PAQUETE!" -o"%~dp0" -y >nul
if errorlevel 1 (echo   [X] !T_EXTRACT_FAIL!&goto :fin)
if exist "%~dp0ComfyUI_windows_portable\python_embeded\python.exe" if not exist "%DESTINO%" ren "%~dp0ComfyUI_windows_portable" "ComfyUI"
if not exist "%PY%" (echo   [X] !T_NO_EMBEDDED!&goto :fin)
if not exist "%MAIN%" (echo   [X] !T_NO_MAIN!&goto :fin)
echo.
echo   !T_BASE_READY!
"%PY%" -s "%~dp0src\instalador.py" "%DESTINO%" "!FABRICANTE!" "!VARIANTE!"
goto :fin
:VERIFICAR_HASH
set "DIGEST="
for /f "delims=" %%H in ('powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $r=Invoke-RestMethod -Headers @{'User-Agent'='CineConIA-Installer'} 'https://api.github.com/repos/Comfy-Org/ComfyUI/releases/latest'; $a=$r.assets ^| Where-Object name -eq '%~1'; if($a.digest){$a.digest}" 2^>nul') do set "DIGEST=%%H"
if not defined DIGEST (
    echo   [!] !T_NO_DIGEST!
    "7zr.exe" t "%~1" >nul 2>&1
    exit /b !errorlevel!
)
set "ESPERADO=!DIGEST:sha256:=!"
set "REAL="
for /f "delims=" %%H in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath '%~1').Hash.ToLower()"') do set "REAL=%%H"
if /I "!REAL!"=="!ESPERADO!" (echo   !T_HASH_OK!&exit /b 0)
exit /b 1
:SELECT_LANGUAGE
set "CULTURE="
set "CINECONIA_LANG="
if /I "%~1"=="--lang=es" set "CINECONIA_LANG=es"
if /I "%~1"=="--lang=en" set "CINECONIA_LANG=en"
if defined CINECONIA_LANG exit /b 0
for /f "delims=" %%L in ('powershell -NoProfile -Command "(Get-Culture).Name" 2^>nul') do set "CULTURE=%%L"
set "CINECONIA_LANG=en"
echo(!CULTURE! | findstr /B /I "es" >nul && set "CINECONIA_LANG=es"
echo.
if /I "!CINECONIA_LANG!"=="es" (
    echo   Idioma detectado: Espanol ^(!CULTURE!^)
    echo     1^) Continuar en Espanol
    echo     2^) Switch to English
    set /p "LANG_CHOICE=   Elige [1]: "
    if "!LANG_CHOICE!"=="2" set "CINECONIA_LANG=en"
) else (
    echo   Detected language: English ^(!CULTURE!^)
    echo     1^) Continue in English
    echo     2^) Cambiar a Espanol
    set /p "LANG_CHOICE=   Choose [1]: "
    if "!LANG_CHOICE!"=="2" set "CINECONIA_LANG=es"
)
exit /b 0
:LOAD_TEXT
if /I "%CINECONIA_LANG%"=="es" (
 set "T_TITLE=Instalador adaptativo de ComfyUI"
 set "T_BANNER=ComfyUI - instalador adaptativo de Cine con IA"
 set "T_ALREADY=ComfyUI ya esta instalado. Analizando el entorno real..."
 set "T_NO_CURL=Falta curl.exe. Se necesita Windows 10 1803 o superior."
 set "T_NO_PS=No se encuentra PowerShell."
 set "T_FREE=Espacio libre"
 set "T_LOW_SPACE=Hay menos de %MIN_ESPACIO_GB% GB libres."
 set "T_GPU_UNKNOWN=No pude identificar automaticamente el fabricante de la GPU."
 set "T_CHOOSE_GPU=Elige"
 set "T_GPU_NONE=No se eligio una GPU compatible."
 set "T_GPU=GPU detectada"
 set "T_VENDOR=Fabricante"
 set "T_PORTABLE=Portable"
 set "T_DOWNLOAD_7Z=Descargando extractor 7-Zip..."
 set "T_DOWNLOAD_7Z_FAIL=No se pudo descargar 7zr.exe."
 set "T_7Z_BAD=7zr.exe no parece ejecutable."
 set "T_EXISTING_BAD=El paquete existente no paso la verificacion; se descargara otra vez."
 set "T_DOWNLOAD_COMFY=Descargando ComfyUI..."
 set "T_DOWNLOAD_COMFY_FAIL=Fallo la descarga de ComfyUI."
 set "T_HASH_FAIL=El SHA-256 no coincide con el publicado por Comfy-Org."
 set "T_INCOMPLETE=Se encontro una carpeta ComfyUI incompleta."
 set "T_BACKUP_REINSTALL=Guardarla como copia y reinstalar? [S/n]:"
 set "T_EXTRACTING=Extrayendo..."
 set "T_EXTRACT_FAIL=Fallo la extraccion."
 set "T_NO_EMBEDDED=No encuentro python_embeded despues de extraer."
 set "T_NO_MAIN=La instalacion no contiene ComfyUI\main.py."
 set "T_BASE_READY=ComfyUI base instalado. Analizando PyTorch y aceleradores reales..."
 set "T_NO_DIGEST=GitHub no entrego digest; se validara el archivo con 7-Zip."
 set "T_HASH_OK=SHA-256 verificado."
 set "T_EXIT=Pulsa una tecla para salir..."
) else (
 set "T_TITLE=Adaptive ComfyUI Installer"
 set "T_BANNER=ComfyUI - adaptive Cine con IA installer"
 set "T_ALREADY=ComfyUI is already installed. Inspecting the real environment..."
 set "T_NO_CURL=curl.exe is missing. Windows 10 1803 or newer is required."
 set "T_NO_PS=PowerShell was not found."
 set "T_FREE=Free space"
 set "T_LOW_SPACE=Less than %MIN_ESPACIO_GB% GB is free."
 set "T_GPU_UNKNOWN=The GPU vendor could not be detected automatically."
 set "T_CHOOSE_GPU=Choose"
 set "T_GPU_NONE=No compatible GPU was selected."
 set "T_GPU=Detected GPU"
 set "T_VENDOR=Vendor"
 set "T_PORTABLE=Portable"
 set "T_DOWNLOAD_7Z=Downloading 7-Zip extractor..."
 set "T_DOWNLOAD_7Z_FAIL=Could not download 7zr.exe."
 set "T_7Z_BAD=7zr.exe does not appear to be executable."
 set "T_EXISTING_BAD=The existing package failed verification and will be downloaded again."
 set "T_DOWNLOAD_COMFY=Downloading ComfyUI..."
 set "T_DOWNLOAD_COMFY_FAIL=ComfyUI download failed."
 set "T_HASH_FAIL=SHA-256 does not match the digest published by Comfy-Org."
 set "T_INCOMPLETE=An incomplete ComfyUI folder was found."
 set "T_BACKUP_REINSTALL=Keep it as a backup and reinstall? [Y/n]:"
 set "T_EXTRACTING=Extracting..."
 set "T_EXTRACT_FAIL=Extraction failed."
 set "T_NO_EMBEDDED=python_embeded was not found after extraction."
 set "T_NO_MAIN=The installation does not contain ComfyUI\main.py."
 set "T_BASE_READY=Base ComfyUI installed. Inspecting real PyTorch and accelerators..."
 set "T_NO_DIGEST=GitHub did not provide a digest; the archive will be tested with 7-Zip."
 set "T_HASH_OK=SHA-256 verified."
 set "T_EXIT=Press any key to exit..."
)
exit /b 0
:fin
echo.
echo   !T_EXIT!
pause >nul
