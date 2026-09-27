@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /D "%~dp0"
chcp 65001 >nul
call :LEER_ARGS %*
call :SELECT_LANGUAGE
rem Paquete ~2 GB + portable extraido ~7 GB + aceleradores y margen.
set "MIN_ESPACIO_GB=15"
set "VERSION=2.6.0"
set "RC=1"
set "CIA_DIR=%~dp0"
call :LOAD_TEXT
title !T_TITLE!
rem Pasos numerados con su cierre en verde (ver :PASO). El visto se pide a
rem PowerShell para que este archivo siga en ASCII; en la consola clasica, "OK".
for /f %%E in ('echo prompt $E^| cmd') do set "ESC=%%E"
set "MK_OK=OK"
if defined WT_SESSION for /f "delims=" %%C in ('powershell -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; [string][char]0x2713"') do set "MK_OK=%%C"
for /f %%T in ('powershell -NoProfile -Command "[DateTimeOffset]::Now.ToUnixTimeSeconds()"') do set "CIA_INICIO=%%T"
set "PASO_N=0"
rem 3 pasos aqui y 9 en src\instalador.py (TITULOS).
set "PASOS_TOTAL=14"
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
    set "RC=!errorlevel!"
    goto :fin
)
call :PASO "!T_STEP_CHECK!"
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
if /I "!FABRICANTE!"=="nvidia" call :ELEGIR_NVIDIA
if /I "!FABRICANTE!"=="nvidia" if not defined VARIANTE goto :fin
if /I "!FABRICANTE!"=="amd" set "VARIANTE=amd"
if /I "!FABRICANTE!"=="intel" set "VARIANTE=intel"
set "PAQUETE=ComfyUI_windows_portable_!VARIANTE!.7z"
echo   !T_PORTABLE!: !PAQUETE!
call :PASO_OK "!GPU!"
call :PASO "!T_STEP_DOWNLOAD!"
if not exist "7zr.exe" (
    echo   !T_DOWNLOAD_7Z!
    if exist "7zr.exe.part" del /Q "7zr.exe.part" >nul 2>&1
    curl.exe --fail --location --retry 5 --retry-delay 2 --progress-bar -o "7zr.exe.part" "https://www.7-zip.org/a/7zr.exe"
    if errorlevel 1 (del /Q "7zr.exe.part" >nul 2>&1&echo   [X] !T_DOWNLOAD_7Z_FAIL!&goto :fin)
    call :BORRAR_BARRA
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
    call :BORRAR_BARRA
    move /Y "!PAQUETE!.part" "!PAQUETE!" >nul
    call :VERIFICAR_HASH "!PAQUETE!"
    if errorlevel 1 (echo   [X] !T_HASH_FAIL!&del /Q "!PAQUETE!" >nul 2>&1&goto :fin)
)
call :PASO_OK "!PAQUETE! - !VERIFY_DETAIL!"
if exist "%DESTINO%" (
    echo.
    echo   !T_INCOMPLETE!
    set /p "REPARAR=   !T_BACKUP_REINSTALL! "
    if /I "!REPARAR!"=="N" goto :fin
    if /I "!REPARAR!"=="NO" goto :fin
    for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "MARCA=%%T"
    ren "%DESTINO%" "ComfyUI_incompleto_!MARCA!"
    if errorlevel 1 goto :fin
)
call :PASO "!T_STEP_EXTRACT!"
rem Extraer en una carpeta NUEVA: nunca borrar otro portable que ya exista.
set "EXTRACT=%~dp0_cineconia_extract_!RANDOM!_!RANDOM!"
if exist "!EXTRACT!" goto :fin
mkdir "!EXTRACT!"
if errorlevel 1 goto :fin
"7zr.exe" x "!PAQUETE!" -o"!EXTRACT!" -y -bso0 -bsp1
if errorlevel 1 (echo   [X] !T_EXTRACT_FAIL!&goto :fin)
if not exist "!EXTRACT!\ComfyUI_windows_portable\python_embeded\python.exe" (echo   [X] !T_NO_EMBEDDED!&goto :fin)
if exist "%DESTINO%" goto :fin
move "!EXTRACT!\ComfyUI_windows_portable" "%DESTINO%" >nul
if errorlevel 1 goto :fin
rem Solo eliminar el directorio de extraccion si quedo vacio.
rmdir "!EXTRACT!" >nul 2>&1
if not exist "%PY%" (echo   [X] !T_NO_EMBEDDED!&goto :fin)
if not exist "%MAIN%" (echo   [X] !T_NO_MAIN!&goto :fin)
rem El paquete ya no hace falta: libera ~2 GB.
del /Q "!PAQUETE!" >nul 2>&1 && echo   !T_CLEANUP!
call :PASO_OK "!T_STEP_READY!"
rem src\instalador.py sigue la numeracion y pone estos pasos en su resumen.
set "CIA_PASOS_BAT=!PASO_N!"
"%PY%" -s "%~dp0src\instalador.py" "%DESTINO%" "!FABRICANTE!" "!VARIANTE!"
set "RC=!errorlevel!"
goto :fin
:PASO
rem Abre un paso: "[n/12] titulo" en ambar.
set /a "PASO_N+=1"
set "PASO_T=%~1"
echo.
echo   !ESC![38;5;179m[!PASO_N!/!PASOS_TOTAL!] !PASO_T!!ESC![0m
exit /b 0
:PASO_OK
rem Cierra el paso en verde con su detalle y lo deja para el resumen final.
set "PASO_D=%~1"
set "CIA_PASO!PASO_N!=!PASO_T!|!PASO_D!"
set "PASO_L=[!PASO_N!/!PASOS_TOTAL!] !PASO_T! ................................................"
set "PASO_L=!PASO_L:~0,49!"
echo   !ESC![38;5;71m!PASO_L! !MK_OK! !PASO_D!!ESC![0m
exit /b 0
:BORRAR_BARRA
rem La barra de curl queda en la linea de arriba: se sube y se borra.
<nul set /p "=!ESC![1A!ESC![2K"
exit /b 0
:VERIFICAR_HASH
rem Sin tuberias: dentro de las comillas de -Command, "^|" llega literal a PowerShell y falla.
set "DIGEST="
for /f "delims=" %%H in ('powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $r=Invoke-RestMethod -Headers @{'User-Agent'='CineConIA-Installer'} 'https://api.github.com/repos/Comfy-Org/ComfyUI/releases/latest'; foreach($a in $r.assets){if($a.name -eq '%~1' -and $a.digest){$a.digest}}" 2^>nul') do set "DIGEST=%%H"
if not defined DIGEST (
    echo   [^^!] !T_NO_DIGEST!
    "7zr.exe" t "%~1" -bso0 -bsp1
    set "HASH_RC=!errorlevel!"
    set "VERIFY_DETAIL=7-Zip OK"
    exit /b !HASH_RC!
)
set "ESPERADO=!DIGEST:sha256:=!"
set "REAL="
for /f "delims=" %%H in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath '%~1').Hash.ToLower()"') do set "REAL=%%H"
if /I "!REAL!"=="!ESPERADO!" (set "VERIFY_DETAIL=!T_STEP_VERIFIED!"&exit /b 0)
exit /b 1
:ELEGIR_NVIDIA
rem Dos portables oficiales: nvidia (CUDA 13, Python 3.13) y nvidia_cu126
rem (CUDA 12.6, Python 3.12). CUDA 13 exige compute capability 7.5+ (serie 16/20
rem o superior) y driver 580+. CUDA 12.6 no trae kernels para Blackwell (serie 50,
rem compute capability 10.0+): ahi solo sirve CUDA 13.
set "VARIANTE=nvidia"
set "NV_MAJOR=0"
set "CC_MAJ="
set "CC_MIN="
set "CC_NUM=0"
set "LEGACY=0"
set "BLACKWELL=0"
where nvidia-smi.exe >nul 2>&1 && (
    for /f "tokens=1 delims=." %%V in ('nvidia-smi --query-gpu^=driver_version --format^=csv^,noheader 2^>nul') do if "!NV_MAJOR!"=="0" set "NV_MAJOR=%%V"
    for /f "tokens=1,2 delims=." %%A in ('nvidia-smi --query-gpu^=compute_cap --format^=csv^,noheader 2^>nul') do if not defined CC_MAJ (set "CC_MAJ=%%A"&set "CC_MIN=%%B")
)
if defined CC_MAJ set /a "CC_NUM=!CC_MAJ!*10+!CC_MIN!" 2>nul
if !CC_NUM! GTR 0 (
    echo   Compute capability: !CC_MAJ!.!CC_MIN!
    if !CC_NUM! LSS 75 set "LEGACY=1"
    if !CC_NUM! GEQ 100 set "BLACKWELL=1"
) else (
    rem Drivers antiguos no informan la compute capability: se deduce por el nombre.
    echo(!GPU! | findstr /I /C:"GTX 10" /C:"GTX 9" /C:"GTX 7" /C:"TITAN X" /C:"TITAN V" /C:"Quadro P" /C:"Quadro M" /C:"Quadro GV" /C:"Tesla P" /C:"Tesla V" /C:"Tesla M" >nul && set "LEGACY=1"
)
if "!LEGACY!"=="1" set "VARIANTE=nvidia_cu126"
if not "!NV_MAJOR!"=="0" echo   Driver NVIDIA: !NV_MAJOR!
if defined CUDA_PEDIDA goto :NV_PEDIDA
if "!NV_MAJOR!"=="0" goto :NV_RECOMENDADA
if !NV_MAJOR! GEQ 580 goto :NV_RECOMENDADA
if "!LEGACY!"=="1" (
    if !NV_MAJOR! LSS 528 echo   [^^!] !T_DRIVER_TOO_OLD!
    goto :NV_RECOMENDADA
)
rem Tarjeta moderna con driver viejo: antes se bajaba a CUDA 12.6 sin preguntar.
rem Ahora se recomienda actualizar el driver y la eleccion queda en manos del usuario.
set "CU126_OK=1"
if "!BLACKWELL!"=="1" set "CU126_OK=0"
if !NV_MAJOR! LSS 528 set "CU126_OK=0"
echo.
echo   [^^!] !T_DRIVER_UPDATE! (!NV_MAJOR!)
if "!BLACKWELL!"=="1" echo   !T_BLACKWELL_ONLY_CU13!
echo.
echo     1^) !T_OPT_UPDATE_DRIVER!
echo     2^) !T_OPT_CU13_ANYWAY!
if "!CU126_OK!"=="1" echo     3^) !T_OPT_CU126_NOW!
if "!CU126_OK!"=="1" (choice /C 123 /N /M "   !T_CHOOSE_GPU! [1-3]: ") else (choice /C 12 /N /M "   !T_CHOOSE_GPU! [1-2]: ")
set "OPC=!errorlevel!"
if "!OPC!"=="1" (
    start "" "https://www.nvidia.com/drivers"
    echo.
    echo   !T_DRIVER_THEN_RERUN!
    set "VARIANTE="
    exit /b 0
)
if "!OPC!"=="3" (set "VARIANTE=nvidia_cu126"&exit /b 0)
echo   [^^!] !T_CU13_NEEDS_580!
exit /b 0
:NV_RECOMENDADA
rem Lista con la recomendada marcada; Enter la acepta, como las demas preguntas.
rem Lo que la tarjeta no soporta se marca y, si se elige, lo frena :NV_PEDIDA.
set "M13="
set "M126="
set "DEF=1"
if "!VARIANTE!"=="nvidia_cu126" set "DEF=2"
if "!DEF!"=="1" (set "M13= !T_RECOMMENDED!") else (set "M126= !T_RECOMMENDED!")
if "!LEGACY!"=="1" set "M13= !T_NOT_COMPATIBLE!"
if "!BLACKWELL!"=="1" set "M126= !T_NOT_COMPATIBLE!"
echo.
echo   !T_CUDA_MENU!
echo     1^) CUDA 13   - Python 3.13 - !T_CU13_DESC!!M13!
echo     2^) CUDA 12.6 - Python 3.12 - !T_CU126_DESC!!M126!
set "OPC="
set /p "OPC=   !T_CHOOSE_GPU! [!DEF!]: "
if not defined OPC exit /b 0
if "!OPC!"=="!DEF!" exit /b 0
if "!OPC!"=="1" (set "CUDA_PEDIDA=13") else if "!OPC!"=="2" (set "CUDA_PEDIDA=12.6") else exit /b 0
:NV_PEDIDA
rem Eleccion manual (menu o --cuda), con protecciones por compute capability.
set "PEDIDA="
if "!CUDA_PEDIDA!"=="13" set "PEDIDA=nvidia"
if "!CUDA_PEDIDA!"=="12.6" set "PEDIDA=nvidia_cu126"
if "!CUDA_PEDIDA!"=="126" set "PEDIDA=nvidia_cu126"
if "!CUDA_PEDIDA!"=="12" set "PEDIDA=nvidia_cu126"
if not defined PEDIDA (
    echo   [^^!] !T_CUDA_BAD_ARG! !CUDA_PEDIDA!
    goto :NV_ELEGIDA
)
if "!PEDIDA!"=="nvidia" if "!LEGACY!"=="1" (
    echo   [X] !T_CU13_BLOCKED!
    goto :NV_ELEGIDA
)
if "!PEDIDA!"=="nvidia_cu126" if "!BLACKWELL!"=="1" (
    echo   [X] !T_CU126_BLOCKED!
    goto :NV_ELEGIDA
)
if !CC_NUM! EQU 0 echo   [^^!] !T_CC_UNKNOWN!
set "VARIANTE=!PEDIDA!"
if "!VARIANTE!"=="nvidia" if not "!NV_MAJOR!"=="0" if !NV_MAJOR! LSS 580 echo   [^^!] !T_CU13_NEEDS_580!
if "!VARIANTE!"=="nvidia_cu126" if not "!NV_MAJOR!"=="0" if !NV_MAJOR! LSS 528 echo   [^^!] !T_DRIVER_TOO_OLD!
:NV_ELEGIDA
call :NV_ETIQUETA "!VARIANTE!"
echo   CUDA: !NV_TXT!
exit /b 0
:NV_ETIQUETA
if /I "%~1"=="nvidia_cu126" (set "NV_TXT=CUDA 12.6 - Python 3.12") else (set "NV_TXT=CUDA 13 - Python 3.13")
exit /b 0
:LEER_ARGS
rem Argumentos opcionales, en cualquier orden: --lang es o en, y --cuda 13 o 12.6.
rem cmd separa los argumentos en "=", asi que --lang=en llega como "--lang" "en".
set "CINECONIA_LANG="
set "CUDA_PEDIDA="
:LEER_ARGS_SIGUIENTE
if "%~1"=="" exit /b 0
if /I "%~1"=="--lang=es" set "CINECONIA_LANG=es"
if /I "%~1"=="--lang=en" set "CINECONIA_LANG=en"
if /I "%~1"=="--lang" (set "CINECONIA_LANG=%~2"&shift)
if /I "%~1"=="--cuda" (set "CUDA_PEDIDA=%~2"&shift)
shift
goto :LEER_ARGS_SIGUIENTE
:SELECT_LANGUAGE
rem Idioma automatico: espanol si la interfaz o el formato regional de Windows
rem estan en espanol; si no, ingles. --lang es / --lang en lo fuerza.
rem (:LEER_ARGS ya dejo CINECONIA_LANG si vino --lang.)
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
 set "T_STEP_CHECK=Revisando el equipo"
 set "T_STEP_DOWNLOAD=Descargando ComfyUI"
 set "T_STEP_EXTRACT=Extrayendo"
 set "T_STEP_VERIFIED=SHA-256 verificado"
 set "T_STEP_READY=listo"
 set "T_EXIT=Pulsa una tecla para salir..."
 set "T_ONEDRIVE=Esta carpeta esta dentro de OneDrive. ComfyUI tiene miles de archivos y OneDrive puede romperlo al sincronizar. Mejor mueve el instalador a una carpeta como C:\ComfyUI o D:\ComfyUI."
 set "T_CONTINUE_ANYWAY=Instalar aqui de todos modos? [s/N]:"
 set "T_NON_ASCII=La ruta contiene tildes, enes u otros caracteres especiales. Algunos nodos fallan con eso; si puedes, usa una ruta simple como C:\ComfyUI."
 set "T_DRIVER_UPDATE=Tu tarjeta sirve para CUDA 13 (la version moderna), pero el driver NVIDIA es anterior al 580"
 set "T_BLACKWELL_ONLY_CU13=Las tarjetas serie 50 solo funcionan con CUDA 13: la version CUDA 12.6 no las soporta."
 set "T_OPT_UPDATE_DRIVER=Actualizar el driver primero (recomendado). Abre la pagina de NVIDIA y cierra el instalador."
 set "T_OPT_CU13_ANYWAY=Instalar CUDA 13 igual y actualizar el driver antes de abrir ComfyUI."
 set "T_OPT_CU126_NOW=Instalar CUDA 12.6: funciona con tu driver actual, pero es la version antigua (Python 3.12)."
 set "T_DRIVER_THEN_RERUN=Instala el driver nuevo, reinicia el PC y vuelve a ejecutar este instalador."
 set "T_CU13_NEEDS_580=CUDA 13 necesita el driver 580 o superior: actualizalo antes de abrir ComfyUI desde https://www.nvidia.com/drivers"
 set "T_CUDA_MENU=Version de CUDA (Enter = recomendada):"
 set "T_CU13_DESC=la mas usada; serie 16/20 o superior, driver 580+"
 set "T_CU126_DESC=compatibilidad: serie 10 o anterior, o nodos que piden CUDA 12"
 set "T_RECOMMENDED=(recomendado)"
 set "T_NOT_COMPATIBLE=(no compatible con tu tarjeta)"
 set "T_CU13_BLOCKED=Tu tarjeta no soporta CUDA 13 (necesita compute capability 7.5 o mas). Se mantiene CUDA 12.6."
 set "T_CU126_BLOCKED=Tu tarjeta serie 50 no funciona con CUDA 12.6. Se mantiene CUDA 13."
 set "T_CC_UNKNOWN=No se pudo leer la compute capability de la tarjeta: se usa tu eleccion sin comprobarla."
 set "T_CUDA_BAD_ARG=Valor de --cuda no reconocido (usa 13 o 12.6):"
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
 set "T_STEP_CHECK=Checking the computer"
 set "T_STEP_DOWNLOAD=Downloading ComfyUI"
 set "T_STEP_EXTRACT=Extracting"
 set "T_STEP_VERIFIED=SHA-256 verified"
 set "T_STEP_READY=done"
 set "T_EXIT=Press any key to exit..."
 set "T_ONEDRIVE=This folder is inside OneDrive. ComfyUI has thousands of files and OneDrive syncing can break it. Move the installer to a folder such as C:\ComfyUI or D:\ComfyUI."
 set "T_CONTINUE_ANYWAY=Install here anyway? [y/N]:"
 set "T_NON_ASCII=The path contains accents or other special characters. Some nodes fail with them; if possible use a simple path such as C:\ComfyUI."
 set "T_DRIVER_UPDATE=Your card supports CUDA 13 (the modern build), but the NVIDIA driver is older than 580"
 set "T_BLACKWELL_ONLY_CU13=50-series cards only work with CUDA 13: the CUDA 12.6 build does not support them."
 set "T_OPT_UPDATE_DRIVER=Update the driver first (recommended). Opens the NVIDIA page and closes the installer."
 set "T_OPT_CU13_ANYWAY=Install CUDA 13 anyway and update the driver before opening ComfyUI."
 set "T_OPT_CU126_NOW=Install CUDA 12.6: works with your current driver, but it is the older build (Python 3.12)."
 set "T_DRIVER_THEN_RERUN=Install the new driver, restart the PC and run this installer again."
 set "T_CU13_NEEDS_580=CUDA 13 needs driver 580 or newer: update it before opening ComfyUI from https://www.nvidia.com/drivers"
 set "T_CUDA_MENU=CUDA version (Enter = recommended):"
 set "T_CU13_DESC=most used; 16/20 series or newer, driver 580+"
 set "T_CU126_DESC=compatibility: 10 series or older, or nodes that need CUDA 12"
 set "T_RECOMMENDED=(recommended)"
 set "T_NOT_COMPATIBLE=(not compatible with your card)"
 set "T_CU13_BLOCKED=Your card does not support CUDA 13 (it needs compute capability 7.5 or higher). Keeping CUDA 12.6."
 set "T_CU126_BLOCKED=Your 50-series card does not work with CUDA 12.6. Keeping CUDA 13."
 set "T_CC_UNKNOWN=The card's compute capability could not be read: your choice is used without checking it."
 set "T_CUDA_BAD_ARG=Unrecognized --cuda value (use 13 or 12.6):"
 set "T_DRIVER_TOO_OLD=The NVIDIA driver is very old and PyTorch may not see the GPU. Update it from https://www.nvidia.com/drivers"
 set "T_RESUME_HINT=Run the installer again: the download will continue where it stopped."
 set "T_CLEANUP=Installation package removed (~2 GB freed)."
)
exit /b 0
:fin
echo.
echo   !T_EXIT!
pause >nul
exit /b !RC!
