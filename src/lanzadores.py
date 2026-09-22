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
if exist ".\ComfyUI\custom_nodes\ComfyUI-Manager\cm-cli.py" .\python_embeded\python.exe -s ".\ComfyUI\custom_nodes\ComfyUI-Manager\cm-cli.py" update all
'''
    close_msg=i18n.t("launcher.close_before_update")
    missing_msg=i18n.t("launcher.updater_missing")
    done_msg=i18n.t("launcher.update_done")
    return f'''@echo off
setlocal
cd /D "%~dp0"
set "PORT={PUERTO}"
for /f %%A in ('powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue) {{1}} else {{0}}"') do set "INUSE=%%A"
if "%INUSE%"=="1" (echo {close_msg}&pause&exit /b 1)
if exist ".\\update\\update_comfyui.bat" (
 call ".\\update\\update_comfyui.bat" nopause
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

def crear_lanzadores(destino,entorno,verificados):
    py=os.path.join(destino,"python_embeded","python.exe")
    nombres=_nombres()
    creados={}
    base=os.path.join(destino,nombres["base"])
    _escribir(base,_inicio("ComfyUI"))
    creados["base"]=base
    if _modulo_ok(py,"comfy_kitchen"):
        r=os.path.join(destino,nombres["kitchen"])
        _escribir(r,_inicio("ComfyUI - Kitchen","--use-ck-attention"))
        creados["kitchen"]=r
    if "sageattention" in verificados:
        r=os.path.join(destino,nombres["sage"])
        _escribir(r,_inicio("ComfyUI - SageAttention","--use-sage-attention"))
        creados["sage"]=r
    if "flashattention" in verificados:
        r=os.path.join(destino,nombres["flash"])
        _escribir(r,_inicio("ComfyUI - FlashAttention","--use-flash-attention"))
        creados["flash"]=r
    if entorno.get("fabricante")=="amd":
        r=os.path.join(destino,nombres["amd"])
        _escribir(r,_inicio("ComfyUI - AMD Dynamic VRAM","--enable-dynamic-vram"))
        creados["amd_dynamic_vram"]=r
    _escribir(os.path.join(destino,nombres["update"]),_actualizador(False))
    _escribir(os.path.join(destino,nombres["update_nodes"]),_actualizador(True))
    return creados, creados.get("sage") or creados.get("kitchen") or creados["base"]

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
