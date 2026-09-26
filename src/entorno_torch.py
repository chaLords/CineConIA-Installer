"""Protege el PyTorch del portable.

Un extra o el requirements.txt de un nodo puede reinstalar PyTorch por su
cuenta (otra version, o la de CPU) y dejar la instalacion rota sin avisar.
Aqui se anota la version antes de cada instalacion y se restaura si cambio.
Tambien se cambia de rama de forma controlada cuando un extra lo exige
(Nunchaku), con vuelta atras automatica si algo deja de cargar.
"""
from __future__ import annotations
import json, os, re, subprocess
from datetime import datetime

PAQUETES=("torch","torchvision","torchaudio")

class EntornoNoRecuperado(RuntimeError):
    """No continuar instalando extras sobre un PyTorch que no pudo recuperarse."""


def restricciones(destino, versiones_base):
    """Evita reemplazar el backend (tambien AMD/Intel) al resolver dependencias."""
    if not versiones_base.get("torch"):
        raise EntornoNoRecuperado("No se pudo registrar la version de PyTorch.")
    carpeta=os.path.join(destino,"_cineconia")
    os.makedirs(carpeta,exist_ok=True)
    ruta=os.path.join(carpeta,"torch-constraints.txt")
    with open(ruta,"w",encoding="utf-8") as f:
        for paquete in PAQUETES:
            if paquete in versiones_base:
                f.write(f"{paquete}=={versiones_base[paquete]}\n")
    return ruta

# Lo minimo que ComfyUI necesita para arrancar despues de tocar PyTorch.
PRUEBA_ARRANQUE = r'''
import torch, torchvision, torchaudio
assert torch.cuda.is_available(), "PyTorch no ve la GPU"
import comfy_kitchen, comfy_aimdo
print(torch.__version__)
'''

def versiones(py):
    codigo=("import importlib.metadata as m,json\nd={}\n"
            f"for p in {PAQUETES!r}:\n"
            "    try: d[p]=m.version(p)\n"
            "    except m.PackageNotFoundError: pass\n"
            "print(json.dumps(d))")
    try:
        r=subprocess.run([py,"-s","-c",codigo],capture_output=True,text=True,timeout=90)
        return json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode==0 else {}
    except (OSError,subprocess.SubprocessError,ValueError,IndexError):
        return {}

def indice(version_torch):
    """Indice oficial de PyTorch para esta build (+cu130 -> .../whl/cu130)."""
    m=re.search(r"\+(cu\d+|xpu)$",version_torch or "")
    return f"https://download.pytorch.org/whl/{m.group(1)}" if m else None

def instalar(py,objetivo,pip):
    """Instala exactamente estas versiones desde el indice de su CUDA."""
    url=indice(objetivo.get("torch"))
    if not url:
        return False
    return pip(py,[f"{p}=={v}" for p,v in objetivo.items()]+["--index-url",url],"PyTorch")

def arranca(py):
    """(ok, detalle): PyTorch, la GPU y las piezas de ComfyUI siguen cargando."""
    try:
        r=subprocess.run([py,"-s","-c",PRUEBA_ARRANQUE],capture_output=True,text=True,timeout=180)
    except (OSError,subprocess.SubprocessError) as e:
        return False,str(e)
    if r.returncode==0:
        return True,r.stdout.strip().splitlines()[-1]
    return False,(r.stderr.strip().splitlines() or ["error"])[-1][:120]

def vigilar(py,antes,pip):
    """Tras instalar algo: si PyTorch cambio, lo restaura. (cambio, restaurado)."""
    despues=versiones(py)
    if not antes or despues==antes:
        return False,True
    return True,(instalar(py,antes,pip) and versiones(py)==antes)

def guardar_estado(destino,py):
    """pip freeze fechado: registro de como estaba todo antes de cambiar PyTorch."""
    carpeta=os.path.join(destino,"_cineconia")
    os.makedirs(carpeta,exist_ok=True)
    ruta=os.path.join(carpeta,datetime.now().strftime("pip-antes-%Y%m%d-%H%M%S.txt"))
    try:
        r=subprocess.run([py,"-s","-m","pip","freeze"],capture_output=True,text=True,timeout=120)
        with open(ruta,"w",encoding="utf-8") as f:
            f.write(r.stdout)
        return ruta
    except (OSError,subprocess.SubprocessError):
        return None

def cambiar_rama(py,rama,version_actual,pip):
    """Cambia PyTorch a la rama dada con la misma CUDA; si algo falla, vuelve atras.

    Devuelve (ok, detalle). torchvision y torchaudio los resuelve pip para que
    coincidan con esa rama de torch.
    """
    antes=versiones(py)
    if not antes.get("torch"):
        return False,"no se pudo registrar PyTorch antes del cambio"
    url=indice(version_actual)
    if not url:
        return False,"sin indice de PyTorch para "+str(version_actual)
    ok=pip(py,[f"torch=={rama[0]}.{rama[1]}.*","torchvision","torchaudio","--index-url",url],"PyTorch")
    listo,detalle=arranca(py) if ok else (False,"pip")
    if listo and detalle.startswith(f"{rama[0]}.{rama[1]}."):
        return True,detalle
    if not instalar(py,antes,pip) or versiones(py)!=antes or not arranca(py)[0]:
        raise EntornoNoRecuperado("PyTorch no pudo recuperarse tras el cambio de rama: "+detalle)
    return False,detalle
