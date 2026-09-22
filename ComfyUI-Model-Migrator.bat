@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /D "%~dp0"
chcp 65001 >nul
call :SELECT_LANGUAGE "%~1"
call :LOAD_TEXT
title !T_TITLE!
set "SCRIPT=%~dp0src\migrar_modelos.py"
set "PYEXE="
set "PYARGS="
echo.
echo   ============================================================
echo     !T_BANNER!
echo   ============================================================
echo.
echo   !T_CLOSE!
echo   !T_SIMULATION!
echo.
if not exist "%SCRIPT%" (echo   [X] !T_NO_SCRIPT!&goto :fin)
if exist "%~dp0ComfyUI\python_embeded\python.exe" (set "PYEXE=%~dp0ComfyUI\python_embeded\python.exe"&goto :ejecutar)
where py.exe >nul 2>&1 && (set "PYEXE=py.exe"&set "PYARGS=-3"&goto :ejecutar)
where python.exe >nul 2>&1 && (set "PYEXE=python.exe"&goto :ejecutar)
echo   !T_NO_PYTHON!
echo   !T_USE_EMBEDDED!
echo.
echo   !T_SELECT_ROOT!
echo   !T_MUST_CONTAIN!
echo.
set "PORTABLE="
for /f "delims=" %%I in ('powershell -NoProfile -Sta -Command "$s=New-Object -ComObject Shell.Application; $f=$s.BrowseForFolder(0,'Select ComfyUI portable / Selecciona ComfyUI portable',0,0); if($f){$f.Self.Path}"') do set "PORTABLE=%%I"
if not defined PORTABLE (echo   [X] !T_NO_FOLDER!&goto :fin)
if exist "!PORTABLE!\python_embeded\python.exe" (set "PYEXE=!PORTABLE!\python_embeded\python.exe"&goto :ejecutar)
if exist "!PORTABLE!\ComfyUI\python_embeded\python.exe" (set "PYEXE=!PORTABLE!\ComfyUI\python_embeded\python.exe"&goto :ejecutar)
echo   [X] !T_BAD_FOLDER!
goto :fin
:ejecutar
echo   Python: !PYEXE!
echo.
"!PYEXE!" !PYARGS! -s "%SCRIPT%"
set "RC=!errorlevel!"
if not "!RC!"=="0" (echo.&echo   [X] !T_EXIT_CODE! !RC!.)
:fin
echo.
echo   !T_EXIT!
pause >nul
exit /b
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
 set "T_TITLE=Migrar modelos de ComfyUI"
 set "T_BANNER=Migrador seguro de modelos de ComfyUI"
 set "T_CLOSE=Cierra ComfyUI antes de comenzar."
 set "T_SIMULATION=El script SIEMPRE muestra una simulacion antes de copiar o mover."
 set "T_NO_SCRIPT=No encuentro src\migrar_modelos.py"
 set "T_NO_PYTHON=No encontre Python en este equipo."
 set "T_USE_EMBEDDED=Puedes usar el Python embebido de cualquier ComfyUI portable existente."
 set "T_SELECT_ROOT=Selecciona la carpeta RAIZ del ComfyUI portable."
 set "T_MUST_CONTAIN=Debe contener python_embeded\python.exe"
 set "T_NO_FOLDER=No se selecciono ninguna carpeta."
 set "T_BAD_FOLDER=Esa carpeta no contiene python_embeded\python.exe"
 set "T_EXIT_CODE=El migrador termino con codigo"
 set "T_EXIT=Pulsa una tecla para salir..."
) else (
 set "T_TITLE=ComfyUI Model Migrator"
 set "T_BANNER=Safe ComfyUI model migrator"
 set "T_CLOSE=Close ComfyUI before starting."
 set "T_SIMULATION=The script ALWAYS shows a simulation before copying or moving."
 set "T_NO_SCRIPT=src\migrar_modelos.py was not found."
 set "T_NO_PYTHON=Python was not found on this computer."
 set "T_USE_EMBEDDED=You can use the embedded Python from any existing ComfyUI portable."
 set "T_SELECT_ROOT=Select the ROOT folder of the ComfyUI portable."
 set "T_MUST_CONTAIN=It must contain python_embeded\python.exe"
 set "T_NO_FOLDER=No folder was selected."
 set "T_BAD_FOLDER=That folder does not contain python_embeded\python.exe"
 set "T_EXIT_CODE=The migrator exited with code"
 set "T_EXIT=Press any key to exit..."
)
exit /b 0
