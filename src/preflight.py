"""Comprobaciones previas y utilidades de Windows."""
from __future__ import annotations
import os
import shutil
import subprocess

def git_exe():
    encontrado = shutil.which("git")
    if encontrado:
        return encontrado
    candidatos = [
        os.path.expandvars(r"%ProgramFiles%\Git\cmd\git.exe"),
        os.path.expandvars(r"%ProgramFiles%\Git\bin\git.exe"),
        os.path.expandvars(r"%LocalAppData%\Programs\Git\cmd\git.exe"),
    ]
    return next((p for p in candidatos if os.path.isfile(p)), None)

def winget_exe():
    return shutil.which("winget")

def instalar_git():
    winget = winget_exe()
    if not winget:
        return False, "winget no esta disponible"
    cmd = [winget, "install", "--id", "Git.Git", "-e", "--source", "winget",
           "--accept-package-agreements", "--accept-source-agreements"]
    try:
        r = subprocess.run(cmd, timeout=900)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    if r.returncode != 0:\n        return False, f"winget devolvio {r.returncode}"\n    return (git_exe() is not None), "Git instalado"

def salud_comfyui(destino):
    faltan = []
    py = os.path.join(destino, "python_embeded", "python.exe")
    main = os.path.join(destino, "ComfyUI", "main.py")
    if not os.path.isfile(py):
        faltan.append(r"python_embeded\python.exe")
    if not os.path.isfile(main):
        faltan.append(r"ComfyUI\main.py")
    if faltan:
        return False, faltan
    try:
        r = subprocess.run([py, "-s", "-c", "import sys; print(sys.version)"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False, ["Python embebido no se puede ejecutar"]
    return (r.returncode == 0), ([] if r.returncode == 0 else ["Python embebido devuelve error"])
