"""Windows preflight checks and utilities."""
from __future__ import annotations
import os
import shutil
import subprocess
import i18n

def git_exe():
    encontrado=shutil.which("git")
    if encontrado:
        return encontrado
    candidatos=[
        os.path.expandvars(r"%ProgramFiles%\Git\cmd\git.exe"),
        os.path.expandvars(r"%ProgramFiles%\Git\bin\git.exe"),
        os.path.expandvars(r"%LocalAppData%\Programs\Git\cmd\git.exe"),
    ]
    return next((p for p in candidatos if os.path.isfile(p)),None)

def winget_exe():
    return shutil.which("winget")

def instalar_git():
    winget=winget_exe()
    if not winget:
        return False,i18n.t("preflight.winget_unavailable")
    cmd=[winget,"install","--id","Git.Git","-e","--source","winget",
         "--accept-package-agreements","--accept-source-agreements"]
    try:
        r=subprocess.run(cmd,timeout=900)
    except (OSError,subprocess.SubprocessError) as e:
        return False,str(e)
    if r.returncode!=0:
        return False,i18n.t("preflight.winget_code",code=r.returncode)
    return (git_exe() is not None),i18n.t("preflight.git_installed")

def vcredist_instalado():
    """True/False si el runtime Visual C++ x64 esta instalado; None si no se sabe.

    Sin el, PyTorch falla al cargar c10.dll y ComfyUI no arranca.
    """
    try:
        import winreg
    except ImportError:
        return None
    for vista in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64",
                                0,winreg.KEY_READ|vista) as k:
                if winreg.QueryValueEx(k,"Installed")[0]==1:
                    return True
        except OSError:
            continue
    sistema=os.path.join(os.environ.get("SystemRoot",r"C:\Windows"),"System32")
    if all(os.path.isfile(os.path.join(sistema,d)) for d in ("msvcp140.dll","vcruntime140_1.dll")):
        return True
    return False

def instalar_vcredist():
    winget=winget_exe()
    if not winget:
        return False,i18n.t("preflight.winget_unavailable")
    cmd=[winget,"install","--id","Microsoft.VCRedist.2015+.x64","-e","--source","winget",
         "--accept-package-agreements","--accept-source-agreements"]
    try:
        r=subprocess.run(cmd,timeout=900)
    except (OSError,subprocess.SubprocessError) as e:
        return False,str(e)
    if r.returncode!=0 and not vcredist_instalado():
        return False,i18n.t("preflight.winget_code",code=r.returncode)
    return True,i18n.t("preflight.vcredist_installed")

def salud_comfyui(destino):
    faltan=[]
    py=os.path.join(destino,"python_embeded","python.exe")
    main=os.path.join(destino,"ComfyUI","main.py")
    if not os.path.isfile(py):
        faltan.append(r"python_embeded\python.exe")
    if not os.path.isfile(main):
        faltan.append(r"ComfyUI\main.py")
    if faltan:
        return False,faltan
    try:
        r=subprocess.run(
            [py,"-s","-c","import sys; print(sys.version)"],
            capture_output=True,text=True,timeout=30
        )
    except (OSError,subprocess.SubprocessError):
        return False,[i18n.t("preflight.python_cannot_run")]
    return (r.returncode==0),([] if r.returncode==0 else [i18n.t("preflight.python_error")])
