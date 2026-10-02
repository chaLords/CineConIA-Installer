"""Detecta el entorno REAL del portable instalado."""
from __future__ import annotations
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import i18n

def _ejecutar(cmd, timeout=25):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""

def driver_nvidia():
    if not shutil.which("nvidia-smi"):
        return None
    salida = _ejecutar(["nvidia-smi","--query-gpu=driver_version,name,memory.total",
                        "--format=csv,noheader,nounits"])
    if not salida:
        return None
    partes = [p.strip() for p in salida.splitlines()[0].split(",")]
    if len(partes) < 3:
        return None
    try: mayor = int(partes[0].split(".")[0])
    except ValueError: mayor = 0
    try: vram = round(float(partes[2]) / 1024, 1)
    except ValueError: vram = 0.0
    return {"version": partes[0], "mayor": mayor, "gpu": partes[1], "vram_gb": vram}

def adaptadores_windows():
    ps = shutil.which("powershell")
    if not ps:
        return []
    script = "$x=Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Select-Object Name,AdapterRAM; $x | ConvertTo-Json -Compress"
    salida = _ejecutar([ps, "-NoProfile", "-Command", script])
    if not salida:
        return []
    try: data = json.loads(salida)
    except ValueError: return []
    return [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])

def entorno_torch(python_exe=None):
    exe = python_exe or sys.executable
    codigo = r'''
import json,re
d={"torch":None,"rama":"","cuda":None,"hip":None,"cuda_available":False,
   "xpu_available":False,"gpu":None,"vram_gb":None,"cap":None,"error":None,"gpu_error":None,"bf16":None}
try:
    import torch
    d["torch"]=torch.__version__
    m=re.match(r"(\d+\.\d+)",torch.__version__ or "")
    d["rama"]=m.group(1) if m else ""
    d["cuda"]=getattr(torch.version,"cuda",None)
    d["hip"]=getattr(torch.version,"hip",None)
    try: d["cuda_available"]=bool(torch.cuda.is_available())
    except Exception: pass
    if (d["cuda"] or d["hip"]) and not d["cuda_available"]:
        try: torch.cuda.init()
        except Exception as e: d["gpu_error"]=str(e).strip().splitlines()[0][:160]
    if d["cuda_available"]:
        try:
            d["gpu"]=torch.cuda.get_device_name(0)
            d["vram_gb"]=round(torch.cuda.get_device_properties(0).total_memory/(1024**3),1)
            d["cap"]=list(torch.cuda.get_device_capability(0))
            d["bf16"]=bool(torch.cuda.is_bf16_supported())
        except Exception: pass
    xpu=getattr(torch,"xpu",None)
    if xpu is not None:
        try: d["xpu_available"]=bool(xpu.is_available())
        except Exception: pass
        if d["xpu_available"]:
            try:
                d["gpu"]=xpu.get_device_name(0)
                d["vram_gb"]=round(xpu.get_device_properties(0).total_memory/(1024**3),1)
            except Exception: pass
except Exception as e:
    d["error"]=f"{type(e).__name__}: {e}"
print(json.dumps(d,ensure_ascii=False))
'''
    salida = _ejecutar([exe, "-s", "-c", codigo], timeout=45)
    if not salida:
        return {"torch":None,"rama":"","cuda":None,"hip":None,"cuda_available":False,
                "xpu_available":False,"gpu":None,"vram_gb":None,"cap":None,
                "error":i18n.t("detection.torch_query_failed")}
    try: return json.loads(salida.splitlines()[-1])
    except ValueError:
        return {"torch":None,"rama":"","cuda":None,"hip":None,"cuda_available":False,
                "xpu_available":False,"gpu":None,"vram_gb":None,"cap":None,
                "error":i18n.t("detection.torch_invalid")}

def espacio_libre_gb(ruta):
    try: return round(shutil.disk_usage(ruta).free / 1e9, 1)
    except OSError: return 0.0

def _fabricante(adaptadores):
    nombres = " | ".join(str(x.get("Name","")) for x in adaptadores).lower()
    if "nvidia" in nombres: return "nvidia"
    if "amd" in nombres or "radeon" in nombres: return "amd"
    if "intel" in nombres or "arc" in nombres: return "intel"
    return None

def informe(python_exe=None, ruta_destino=None, fabricante_hint=None, variante=None):
    torch = entorno_torch(python_exe)
    nvidia = driver_nvidia()
    adaptadores = adaptadores_windows()
    if torch.get("hip"):
        fabricante, backend = "amd", f"ROCm/HIP {torch['hip']}"
    elif torch.get("xpu_available"):
        fabricante, backend = "intel", "Intel XPU"
    elif torch.get("cuda_available") or torch.get("cuda"):
        fabricante, backend = "nvidia", f"CUDA {torch.get('cuda') or i18n.t('detection.cuda_unknown')}"
    else:
        fabricante, backend = fabricante_hint or _fabricante(adaptadores), i18n.t("detection.no_accelerator")
    gpu, vram = torch.get("gpu"), torch.get("vram_gb")
    if not gpu and nvidia:
        gpu, vram = nvidia["gpu"], nvidia["vram_gb"]
    if not gpu and adaptadores:
        gpu = " | ".join(str(x.get("Name","")) for x in adaptadores if x.get("Name"))
    # PyTorch compilado para GPU que no puede usarla: casi siempre es un
    # driver demasiado antiguo para la version de CUDA/ROCm del portable.
    gpu_inutilizable = bool(torch.get("torch")) and (
        (bool(torch.get("cuda") or torch.get("hip")) and not torch.get("cuda_available"))
        or (fabricante=="intel" and not torch.get("xpu_available"))
        or (fabricante in ("nvidia","amd") and not torch.get("cuda_available")))
    try: hardware = json.loads(os.environ.get("CIA_BOOTSTRAP_HARDWARE", "{}"))
    except ValueError: hardware = {}
    return {
        "hardware": hardware,
        "gpu_inutilizable": gpu_inutilizable,
        "gpu_error": torch.get("gpu_error"),
        "so": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "fabricante": fabricante or i18n.t("detection.unknown"),
        "variante_portable": variante,
        "backend": backend,
        "gpu": gpu or i18n.t("detection.gpu_unknown"),
        "vram_gb": vram,
        "driver": nvidia,
        "torch": torch,
        "torch_rama": torch.get("rama") or "",
        "cuda": torch.get("cuda"),
        "hip": torch.get("hip"),
        "xpu": bool(torch.get("xpu_available")),
        "capacidad": tuple(torch["cap"]) if torch.get("cap") else None,
        "espacio_gb": espacio_libre_gb(ruta_destino or os.getcwd()),
        "adaptadores": adaptadores,
    }
