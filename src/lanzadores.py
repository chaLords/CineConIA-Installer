"""Generate launchers and the single ComfyUI desktop shortcut."""
from __future__ import annotations
import os, subprocess, urllib.error, urllib.request
import i18n

ICONO_URL="https://raw.githubusercontent.com/Comfy-Org/docs/main/favicon.ico"
PUERTO=8188

def _escribir(ruta,contenido):
    with open(ruta,"w",encoding="utf-8",newline="\r\n") as f:
        f.write(contenido)

def _inicio(titulo,flags=""):
    flags=(" "+flags.strip()) if flags.strip() else ""
    missing_python=i18n.t("launcher.missing_python")
    missing_main=i18n.t("launcher.missing_main")
    comfy_error=i18n.t("launcher.comfy_error")
    return f'''@echo off
setlocal
chcp 65001 >nul
cd /D "%~dp0"
title {titulo}
set "PORT={PUERTO}"
if not exist ".\\python_embeded\\python.exe" (echo {missing_python}&pause&exit /b 1)
if not exist ".\\ComfyUI\\main.py" (echo {missing_main}&pause&exit /b 1)
for /f %%A in ('powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue) {{1}} else {{0}}"') do set "INUSE=%%A"
if "%INUSE%"=="1" (start "" "http://127.0.0.1:%PORT%"&exit /b 0)
.\\python_embeded\\python.exe -s ComfyUI\\main.py --windows-standalone-build --port %PORT%{flags}
if errorlevel 1 echo {comfy_error}
pause
'''

def _actualizador(nodos=False):
    extra=""
    if nodos:
        extra=r'''
if exist ".\ComfyUI\custom_nodes\ComfyUI-Cine-con-IA\.git" git -C ".\ComfyUI\custom_nodes\ComfyUI-Cine-con-IA" pull --ff-only
set "COMFYUI_PATH=%~dp0ComfyUI"
if exist ".\python_embeded\Lib\site-packages\cm_cli\__main__.py" (
 rem Snapshot antes de actualizar: se puede volver atras desde el Manager.
 .\python_embeded\python.exe -s -m cm_cli save-snapshot
 .\python_embeded\python.exe -s -m cm_cli update all
) else if exist ".\ComfyUI\custom_nodes\ComfyUI-Manager\cm-cli.py" (
 .\python_embeded\python.exe -s ".\ComfyUI\custom_nodes\ComfyUI-Manager\cm-cli.py" save-snapshot
 .\python_embeded\python.exe -s ".\ComfyUI\custom_nodes\ComfyUI-Manager\cm-cli.py" update all
)
'''
    close_msg=i18n.t("launcher.close_before_update")
    missing_msg=i18n.t("launcher.updater_missing")
    done_msg=i18n.t("launcher.update_done")
    return f'''@echo off
setlocal
chcp 65001 >nul
cd /D "%~dp0"
set "PORT={PUERTO}"
for /f %%A in ('powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue) {{1}} else {{0}}"') do set "INUSE=%%A"
if "%INUSE%"=="1" (echo {close_msg}&pause&exit /b 1)
rem Los scripts oficiales usan rutas ..\\ relativas: hay que entrar en update\\.
rem Se prefiere la version estable; la otra sigue la rama de desarrollo.
set "UPD="
if exist ".\\update\\update_comfyui.bat" set "UPD=update_comfyui.bat"
if exist ".\\update\\update_comfyui_stable.bat" set "UPD=update_comfyui_stable.bat"
if defined UPD (
 pushd ".\\update"
 call ".\\%UPD%" nopause
 popd
) else (
 if exist ".\\ComfyUI\\.git" (git -C ".\\ComfyUI" pull --ff-only) else (echo {missing_msg}&pause&exit /b 1)
)
{extra}
echo {done_msg}
pause
'''

def _modulo_ok(py,modulo):
    try:
        return subprocess.run(
            [py,"-s","-c",f"import {modulo}"],capture_output=True,timeout=45
        ).returncode==0
    except (OSError,subprocess.SubprocessError):
        return False

def _nombres():
    if i18n.get_language()=="es":
        return {
            "base":"Iniciar-ComfyUI.bat",
            "kitchen":"Iniciar-ComfyUI-Kitchen.bat",
            "sage":"Iniciar-ComfyUI-SageAttention.bat",
            "flash":"Iniciar-ComfyUI-FlashAttention.bat",
            "amd":"Iniciar-ComfyUI-DynamicVRAM.bat",
            "update":"Actualizar-ComfyUI.bat",
            "update_nodes":"Actualizar-ComfyUI-y-Nodos.bat",
        }
    return {
        "base":"Start-ComfyUI.bat",
        "kitchen":"Start-ComfyUI-Kitchen.bat",
        "sage":"Start-ComfyUI-SageAttention.bat",
        "flash":"Start-ComfyUI-FlashAttention.bat",
        "amd":"Start-ComfyUI-DynamicVRAM.bat",
        "update":"Update-ComfyUI.bat",
        "update_nodes":"Update-ComfyUI-and-Nodes.bat",
    }

def flag_soportado(destino,flag):
    """El flag existe en esta version de ComfyUI (evita lanzadores que no arrancan)."""
    try:
        with open(os.path.join(destino,"ComfyUI","comfy","cli_args.py"),encoding="utf-8") as f:
            return f'"{flag}"' in f.read()
    except OSError:
        return False

def manager_disponible(destino):
    py=os.path.join(destino,"python_embeded","python.exe")
    return flag_soportado(destino,"--enable-manager") and _modulo_ok(py,"comfyui_manager")

def crear_lanzadores(destino,entorno,verificados):
    py=os.path.join(destino,"python_embeded","python.exe")
    nombres=_nombres()
    comun="--enable-manager" if manager_disponible(destino) else ""
    creados={}
    def lanzador(clave,titulo,flag=""):
        r=os.path.join(destino,nombres[clave])
        _escribir(r,_inicio(titulo,f"{comun} {flag}"))
        creados[clave]=r
    lanzador("base","ComfyUI")
    if _modulo_ok(py,"comfy_kitchen") and flag_soportado(destino,"--use-ck-attention"):
        lanzador("kitchen","ComfyUI - Kitchen","--use-ck-attention")
    if "sageattention" in verificados:
        lanzador("sage","ComfyUI - SageAttention","--use-sage-attention")
    if "flashattention" in verificados:
        lanzador("flash","ComfyUI - FlashAttention","--use-flash-attention")
    if entorno.get("fabricante")=="amd" and flag_soportado(destino,"--enable-dynamic-vram"):
        lanzador("amd","ComfyUI - AMD Dynamic VRAM","--enable-dynamic-vram")
    _escribir(os.path.join(destino,nombres["update"]),_actualizador(False))
    _escribir(os.path.join(destino,nombres["update_nodes"]),_actualizador(True))
    # Kitchen solo esta medido en CUDA; en AMD/Intel el acceso usa el backend oficial.
    kitchen=creados.get("kitchen") if entorno.get("fabricante")=="nvidia" else None
    return creados, creados.get("sage") or kitchen or creados["base"]

def _descargar_icono(destino):
    ruta=os.path.join(destino,"ComfyUI.ico")
    if os.path.isfile(ruta) and os.path.getsize(ruta)>0:
        return ruta
    try:
        req=urllib.request.Request(ICONO_URL,headers={"User-Agent":"CineConIA-Installer"})
        with urllib.request.urlopen(req,timeout=25) as r:
            data=r.read()
        if len(data)<100:
            return None
        with open(ruta,"wb") as f:
            f.write(data)
        return ruta
    except (OSError,urllib.error.URLError):
        return None

def crear_acceso_escritorio(destino,lanzador):
    icono=_descargar_icono(destino)
    q=lambda v:str(v).replace("'","''")
    icon=f"$s.IconLocation='{q(icono)},0';" if icono else ""
    script=("$w=New-Object -ComObject WScript.Shell;"
            "$d=[Environment]::GetFolderPath('Desktop');"
            "$s=$w.CreateShortcut((Join-Path $d 'ComfyUI.lnk'));"
            f"$s.TargetPath='{q(os.path.abspath(lanzador))}';"
            f"$s.WorkingDirectory='{q(os.path.abspath(destino))}';"
            "$s.Description='ComfyUI';"+icon+"$s.Save()")
    try:
        r=subprocess.run(
            ["powershell.exe","-NoProfile","-Command",script],
            capture_output=True,text=True,timeout=30
        )
    except (OSError,subprocess.SubprocessError) as e:
        return False,str(e)
    return (r.returncode==0), (icono if r.returncode==0 else (r.stderr.strip() or "PowerShell error"))
