"""Qué hay en este equipo y qué le conviene.

La pregunta que resuelve este módulo no es "¿qué CUDA soporta el driver?"
sino "¿qué CUDA le conviene a esta tarjeta?". No son lo mismo, y confundirlas
es lo que lleva a instalar una rama para la que luego no hay ruedas.
"""
import os
import platform
import re
import shutil
import subprocess
import sys

# Arquitecturas NVIDIA por capacidad de cómputo. El número mayor es el que
# manda: 12.x es Blackwell (RTX 50xx), 8.9 es Ada (RTX 40xx), 8.6 Ampere.
ARQUITECTURAS = {
    12: "Blackwell (RTX 50xx)",
    10: "Blackwell datacenter",
    9: "Hopper",
    8: "Ada / Ampere (RTX 30xx-40xx)",
    7: "Turing / Volta (RTX 20xx, GTX 16xx)",
    6: "Pascal (GTX 10xx)",
}

# Driver mínimo por rama de CUDA en Windows.
DRIVER_MINIMO = {"12.8": 525, "13.0": 580}


def _ejecutar(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def driver_nvidia():
    """Versión del driver y nombre de la GPU, leídos de nvidia-smi."""
    if not shutil.which("nvidia-smi"):
        return None
    salida = _ejecutar([
        "nvidia-smi",
        "--query-gpu=driver_version,name,memory.total",
        "--format=csv,noheader,nounits",
    ])
    if not salida:
        return None
    partes = [p.strip() for p in salida.splitlines()[0].split(",")]
    if len(partes) < 3:
        return None
    version = partes[0]
    try:
        mayor = int(version.split(".")[0])
    except ValueError:
        mayor = 0
    try:
        vram = round(float(partes[2]) / 1024, 1)
    except ValueError:
        vram = 0.0
    return {"version": version, "mayor": mayor, "gpu": partes[1], "vram_gb": vram}


def torch_instalado(python_exe=None):
    """Qué torch hay, si hay alguno. Devuelve None si no está instalado."""
    exe = python_exe or sys.executable
    salida = _ejecutar([
        exe, "-c",
        "import torch,json;"
        "print(json.dumps({'torch':torch.__version__,'cuda':torch.version.cuda,"
        "'cap':list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None}))",
    ])
    if not salida:
        return None
    import json
    try:
        d = json.loads(salida.splitlines()[-1])
    except ValueError:
        return None
    # "2.8.0+cu128" -> "2.8"
    m = re.match(r"(\d+\.\d+)", d.get("torch") or "")
    d["rama"] = m.group(1) if m else ""
    return d


def capacidad_computo(python_exe=None):
    """(mayor, menor) de la GPU. Necesita torch; None si aún no está."""
    t = torch_instalado(python_exe)
    return tuple(t["cap"]) if t and t.get("cap") else None


def espacio_libre_gb(ruta):
    try:
        return round(shutil.disk_usage(ruta).free / 1e9, 1)
    except OSError:
        return 0.0


def recomendar_cuda(drv, capacidad=None):
    """Qué rama de CUDA conviene, y por qué.

    Devuelve (rama, motivo, disponibles). El motivo se enseña al usuario:
    una recomendación sin explicación es indistinguible de una imposición,
    y el objetivo de este instalador es justo que se pueda elegir.
    """
    if not drv:
        return None, "No se detectó ninguna GPU NVIDIA.", []

    disponibles = [c for c, minimo in DRIVER_MINIMO.items() if drv["mayor"] >= minimo]
    if not disponibles:
        return (None,
                f"Tu driver ({drv['version']}) es anterior al mínimo para CUDA. "
                f"Actualízalo desde la web de NVIDIA.", [])

    mayor_cap = capacidad[0] if capacidad else None

    # Blackwell necesita CUDA 13: las ruedas de cu128 no traen su arquitectura.
    if mayor_cap and mayor_cap >= 12:
        if "13.0" in disponibles:
            return "13.0", "Tu GPU es Blackwell y necesita CUDA 13.0.", disponibles
        return (disponibles[-1],
                f"Tu GPU es Blackwell y pide CUDA 13.0, pero tu driver "
                f"({drv['version']}) no llega. Actualiza el driver.", disponibles)

    # Todo lo anterior a Blackwell va mejor en 12.8: es donde hay más ruedas
    # compiladas de SageAttention, Triton y compañía.
    if "12.8" in disponibles:
        arq = ARQUITECTURAS.get(mayor_cap, "tu GPU") if mayor_cap else "tu GPU"
        return ("12.8",
                f"{arq} funciona igual de rápido en CUDA 12.8, y es la rama "
                f"con más aceleradores compilados para Windows.", disponibles)

    return disponibles[-1], "Única rama compatible con tu driver.", disponibles


def informe(python_exe=None, ruta_destino=None):
    """Todo lo detectado, en un diccionario."""
    drv = driver_nvidia()
    t = torch_instalado(python_exe)
    cap = tuple(t["cap"]) if t and t.get("cap") else None
    rama, motivo, disponibles = recomendar_cuda(drv, cap)
    return {
        "so": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "driver": drv,
        "torch": t,
        "capacidad": cap,
        "arquitectura": ARQUITECTURAS.get(cap[0]) if cap else None,
        "cuda_recomendada": rama,
        "cuda_motivo": motivo,
        "cuda_disponibles": disponibles,
        "espacio_gb": espacio_libre_gb(ruta_destino or os.getcwd()),
    }
