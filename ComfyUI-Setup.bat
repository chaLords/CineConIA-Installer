@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /D "%~dp0"
chcp 65001 >nul
call :SELECT_LANGUAGE "%~1" "%~2"
rem Paquete ~2 GB + portable extraido ~7 GB + aceleradores y margen.
set "MIN_ESPACIO_GB=15"
set "VERSION=2.0.0"
set "CIA_DIR=%~dp0"
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
rem OneDrive sincroniza (y puede dejar "solo en la nube") miles de archivos del
rem portable; una ruta con tildes o enes rompe algunos nodos y paquetes pip.
echo(!CIA_DIR! | findstr /I /C:"OneDrive" >nul && (
    echo   [^^!] !T_ONEDRIVE!
    set /p "SEGUIR=   !T_CONTINUE_ANYWAY! "
    if /I not "!SEGUIR!"=="S" if /I not "!SEGUIR!"=="Y" goto :fin
)
powershell -NoProfile -Command "if ($env:CIA_DIR -match '[^\x00-\x7F]') { exit 1 } else { exit 0 }"
if errorlevel 1 echo   [^^!] !T_NON_ASCII!
rem GB enteros: con Windows en espanol un decimal sale como "9,5" y se leia 95.
for /f %%G in ('powershell -NoProfile -Command "[int][math]::Floor((Get-PSDrive -Name ([IO.Path]::GetPathRoot($env:CIA_DIR).Substring(0,1))).Free/1GB)"') do set "ESPACIO=%%G"
if defined ESPACIO (
    echo   !T_FREE!: !ESPACIO! GB
    if !ESPACIO! LSS %MIN_ESPACIO_GB% (echo   [X] !T_LOW_SPACE!&goto :fin)
)
where nvidia-smi.exe >nul 2>&1 && (
    for /f "tokens=*" %%G in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do if not defined GPU set "GPU=%%G"
    if defined GPU set "FABRICANTE=nvidia"
)
if not defined FABRICANTE (
    for /f "delims=" %%G in ('powershell -NoProfile -Command "(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue).Name -join ' / '"') do set "GPU=%%G"
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
    rem CUDA 13 exige compute capability 7.5+ (Turing o superior) y driver 580+.
    set "LEGACY=0"
    set "CC_MAJ="
    set "CC_MIN="
    where nvidia-smi.exe >nul 2>&1 && (
        for /f "tokens=1,2 delims=." %%A in ('nvidia-smi --query-gpu^=compute_cap --format^=csv^,noheader 2^>nul') do if not defined CC_MAJ (set "CC_MAJ=%%A"&set "CC_MIN=%%B")
    )
    set "CC_NUM=0"
    if defined CC_MAJ set /a "CC_NUM=!CC_MAJ!*10+!CC_MIN!" 2>nul
    if !CC_NUM! GTR 0 (
        echo   Compute capability: !CC_MAJ!.!CC_MIN!
        if !CC_NUM! LSS 75 set "LEGACY=1"
    ) else (
        echo(!GPU! | findstr /I /C:"GTX 10" /C:"GTX 9" /C:"GTX 7" /C:"TITAN X" /C:"TITAN V" /C:"Quadro P" /C:"Quadro M" /C:"Quadro GV" /C:"Tesla P" /C:"Tesla V" /C:"Tesla M" >nul && set "LEGACY=1"
    )
    if not "!NV_MAJOR!"=="0" if !NV_MAJOR! LSS 580 (
        if "!LEGACY!"=="0" echo   [^^!] !T_DRIVER_UPDATE! ^(!NV_MAJOR!^)
        set "LEGACY=1"
    )
    if not "!NV_MAJOR!"=="0" if !NV_MAJOR! LSS 528 echo   [^^!] !T_DRIVER_TOO_OLD!
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
    rem -C - reanuda un .part previo: un corte al 90%% no obliga a bajar 2 GB otra vez.
    rem Si el .part fuera de otra version, el SHA-256 lo detecta y se descarta.
    curl.exe --fail --location --retry 5 --retry-delay 2 -C - --progress-bar -o "!PAQUETE!.part" "https://github.com/Comfy-Org/ComfyUI/releases/latest/download/!PAQUETE!"
    if errorlevel 1 (echo   [X] !T_DOWNLOAD_COMFY_FAIL!&echo   !T_RESUME_HINT!&goto :fin)
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
"7zr.exe" x "!PAQUETE!" -o"%~dp0" -y -bso0 -bsp1
if errorlevel 1 (echo   [X] !T_EXTRACT_FAIL!&goto :fin)
if exist "%~dp0ComfyUI_windows_portable\python_embeded\python.exe" if not exist "%DESTINO%" ren "%~dp0ComfyUI_windows_portable" "ComfyUI"
if not exist "%PY%" (echo   [X] !T_NO_EMBEDDED!&goto :fin)
if not exist "%MAIN%" (echo   [X] !T_NO_MAIN!&goto :fin)
rem El paquete ya no hace falta: libera ~2 GB.
del /Q "!PAQUETE!" >nul 2>&1 && echo   !T_CLEANUP!
echo.
echo   !T_BASE_READY!
"%PY%" -s "%~dp0src\instalador.py" "%DESTINO%" "!FABRICANTE!" "!VARIANTE!"
goto :fin
:VERIFICAR_HASH
rem Sin tuberias: dentro de las comillas de -Command, "^|" llega literal a PowerShell y falla.
set "DIGEST="
for /f "delims=" %%H in ('powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $r=Invoke-RestMethod -Headers @{'User-Agent'='CineConIA-Installer'} 'https://api.github.com/repos/Comfy-Org/ComfyUI/releases/latest'; foreach($a in $r.assets){if($a.name -eq '%~1' -and $a.digest){$a.digest}}" 2^>nul') do set "DIGEST=%%H"
if not defined DIGEST (
    echo   [^^!] !T_NO_DIGEST!
    "7zr.exe" t "%~1" -bso0 -bsp1
    exit /b !errorlevel!
)
set "ESPERADO=!DIGEST:sha256:=!"
set "REAL="
for /f "delims=" %%H in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath '%~1').Hash.ToLower()"') do set "REAL=%%H"
if /I "!REAL!"=="!ESPERADO!" (echo   !T_HASH_OK!&exit /b 0)
exit /b 1
:SELECT_LANGUAGE
rem Idioma automatico: espanol si la interfaz o el formato regional de Windows
rem estan en espanol; si no, ingles. --lang es / --lang en lo fuerza.
rem cmd separa los argumentos en "=", asi que --lang=en llega como "--lang" "en".
set "CINECONIA_LANG="
if /I "%~1"=="--lang" set "CINECONIA_LANG=%~2"
if /I "%~1"=="--lang=es" set "CINECONIA_LANG=es"
if /I "%~1"=="--lang=en" set "CINECONIA_LANG=en"
if /I "!CINECONIA_LANG!"=="es" exit /b 0
if /I "!CINECONIA_LANG!"=="en" exit /b 0
set "CINECONIA_LANG=en"
for /f "delims=" %%L in ('powershell -NoProfile -Command "(Get-UICulture).Name; (Get-Culture).Name" 2^>nul') do (
    echo(%%L| findstr /B /I "es" >nul && set "CINECONIA_LANG=es"
)
exit /b 0
:LOAD_TEXT
if /I "%CINECONIA_LANG%"=="es" (
 set "T_TITLE=Instalador adaptativo de ComfyUI"
 set "T_BANNER=ComfyUI - instalador adaptativo de Cine con IA v%VERSION%"
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
 set "T_ONEDRIVE=Esta carpeta esta dentro de OneDrive. ComfyUI tiene miles de archivos y OneDrive puede romperlo al sincronizar. Mejor mueve el instalador a una carpeta como C:\ComfyUI o D:\ComfyUI."
 set "T_CONTINUE_ANYWAY=Instalar aqui de todos modos? [s/N]:"
 set "T_NON_ASCII=La ruta contiene tildes, enes u otros caracteres especiales. Algunos nodos fallan con eso; si puedes, usa una ruta simple como C:\ComfyUI."
 set "T_DRIVER_UPDATE=Tu driver NVIDIA es anterior al 580. Se instalara la version compatible (CUDA 12.6). Si actualizas el driver, el instalador usara la version moderna (CUDA 13)."
 set "T_DRIVER_TOO_OLD=El driver NVIDIA es muy antiguo y PyTorch podria no ver la GPU. Actualizalo desde https://www.nvidia.com/drivers"
 set "T_RESUME_HINT=Vuelve a ejecutar el instalador: la descarga continuara donde quedo."
 set "T_CLEANUP=Paquete de instalacion eliminado (se liberaron ~2 GB)."
) else (
 set "T_TITLE=Adaptive ComfyUI Installer"
 set "T_BANNER=ComfyUI - adaptive Cine con IA installer v%VERSION%"
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
 set "T_ONEDRIVE=This folder is inside OneDrive. ComfyUI has thousands of files and OneDrive syncing can break it. Move the installer to a folder such as C:\ComfyUI or D:\ComfyUI."
 set "T_CONTINUE_ANYWAY=Install here anyway? [y/N]:"
 set "T_NON_ASCII=The path contains accents or other special characters. Some nodes fail with them; if possible use a simple path such as C:\ComfyUI."
 set "T_DRIVER_UPDATE=Your NVIDIA driver is older than 580. The compatible build (CUDA 12.6) will be installed. After a driver update the installer will use the modern build (CUDA 13)."
 set "T_DRIVER_TOO_OLD=The NVIDIA driver is very old and PyTorch may not see the GPU. Update it from https://www.nvidia.com/drivers"
 set "T_RESUME_HINT=Run the installer again: the download will continue where it stopped."
 set "T_CLEANUP=Installation package removed (~2 GB freed)."
)
exit /b 0
:fin
echo.
echo   !T_EXIT!
pause >nul
