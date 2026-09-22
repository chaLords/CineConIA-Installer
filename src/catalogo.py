"""Catalogo adaptativo de aceleradores."""
from __future__ import annotations
import io, json, os, re, urllib.error, urllib.request, zipfile
import i18n

TIEMPO_ESPERA = 25
# Cabeceras y .lib de Python que publica triton-windows para Python embebido.
CABECERAS_RELEASE = "woct0rdho/triton-windows/releases/tags/v3.0.0-windows.post1"

PERFILES = {
    "sage":{"herramientas":["triton","sageattention"],"vram_min":0},
    "flash":{"herramientas":["flashattention"],"vram_min":0},
    "flux":{"herramientas":["triton","nunchaku"],"vram_min":6},
    "caras":{"herramientas":["insightface","onnxruntime"],"vram_min":4},
}

# Prueba funcional: un import que funciona no garantiza que los kernels
# corran en esta GPU. Se ejecuta una operacion real y minima.
PRUEBA_SAGE = r'''
import torch
from sageattention import sageattn
q=torch.randn(1,8,256,64,dtype=torch.float16,device="cuda")
o=sageattn(q,q,q,tensor_layout="HND",is_causal=False)
torch.cuda.synchronize()
assert torch.isfinite(o).all().item()
import sageattention; print(getattr(sageattention,"__version__","OK"))
'''
PRUEBA_FLASH = r'''
import torch
from flash_attn import flash_attn_func
q=torch.randn(1,256,8,64,dtype=torch.float16,device="cuda")
o=flash_attn_func(q,q,q)
torch.cuda.synchronize()
assert torch.isfinite(o).all().item()
import flash_attn; print(flash_attn.__version__)
'''

HERRAMIENTAS = {
    "triton":{"nombre":"Triton","para":"Runtime para kernels.","fuente":"triton","paquete":"triton-windows","modulo":"triton","fabricantes":{"nvidia"},
              "licencia":"MIT - woct0rdho/triton-windows"},
    "sageattention":{"nombre":"SageAttention 2","para":"Acelera atencion si existe wheel exacta.","fuente":"github","repo":"woct0rdho/SageAttention","modulo":"sageattention","prueba":PRUEBA_SAGE,"fabricantes":{"nvidia"},"licencia":"Apache-2.0"},
    "flashattention":{"nombre":"FlashAttention","para":"Backend alternativo.","fuente":"github","repo":"kingbri1/flash-attention","modulo":"flash_attn","prueba":PRUEBA_FLASH,"fabricantes":{"nvidia"},"licencia":"BSD-3-Clause"},
    "nunchaku":{"nombre":"Nunchaku","para":"Cuantizacion 4-bit.","fuente":"github","repo":"nunchux-ai/nunchaku","modulo":"nunchaku","fabricantes":{"nvidia"},"licencia":"Apache-2.0"},
    "insightface":{"nombre":"InsightFace","para":"Analisis facial.","fuente":"pypi","paquete":"insightface","modulo":"insightface","fabricantes":{"nvidia","amd","intel"},"licencia":"MIT"},
    "onnxruntime":{"nombre":"ONNX Runtime","para":"Runtime ONNX.","fuente":"pypi","modulo":"onnxruntime","fabricantes":{"nvidia","amd","intel"},
                   "paquete_por_fabricante":{"nvidia":"onnxruntime-gpu","amd":"onnxruntime","intel":"onnxruntime"},"licencia":"MIT"},
}

def herramientas_de(perfiles):
    vistas, salida = set(), []
    for clave in perfiles:
        for h in PERFILES.get(clave,{}).get("herramientas",[]):
            if h not in vistas:
                vistas.add(h); salida.append(h)
    orden=list(HERRAMIENTAS)
    return sorted(salida,key=orden.index)

def _json(url):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"CineConIA-Installer"})
    with urllib.request.urlopen(req,timeout=TIEMPO_ESPERA) as r:
        return json.loads(r.read().decode("utf-8"))

def _releases(repo):
    return _json(f"https://api.github.com/repos/{repo}/releases?per_page=30")

def _version(texto):
    m=re.match(r"(\d+)\.(\d+)",texto or "")
    return (int(m.group(1)),int(m.group(2))) if m else None

def _torch_de_rueda(nombre):
    """(version, andhigher) declarada en el nombre de la wheel."""
    m=re.search(r"torch(\d+)\.(\d+)(?:\.\d+)?(andhigher)?",nombre)
    if m:
        return (int(m.group(1)),int(m.group(2))),bool(m.group(3))
    m=re.search(r"torch(\d)(\d{1,2})(?!\d)",nombre)
    if m:
        return (int(m.group(1)),int(m.group(2))),False
    return None,False

def _puntua(nombre,torch_rama,cuda,py_tag):
    n=(nombre or "").lower()
    if not n.endswith(".whl") or "win_amd64" not in n or not cuda or not torch_rama:
        return None
    may,_,men=cuda.partition("."); men=men or "0"
    if not re.search(rf"cu{re.escape(may)}\.?{re.escape(men)}(?!\d)",n): return None
    instalada=_version(torch_rama)
    rueda,y_superior=_torch_de_rueda(n)
    if not instalada or not rueda: return None
    if rueda==instalada: exacta=2
    elif y_superior and instalada>rueda: exacta=1
    else: return None
    # abi3 y la etiqueta exacta valen lo mismo: ante un empate gana la
    # release mas reciente, que es la primera que devuelve GitHub.
    if "abi3" in n or py_tag.lower() in n: py=2
    elif re.search(r"cp\d{2,3}",n): return None
    else: py=1
    return exacta*10+py

def buscar_rueda(repo,torch_rama,cuda,py_tag):
    try: releases=_releases(repo)
    except (urllib.error.URLError,OSError,ValueError) as e:
        return None,i18n.t("catalog.query_failed",repo=repo,error=type(e).__name__)
    mejor,punt=None,-1
    for rel in releases:
        if rel.get("draft") or rel.get("prerelease"): continue
        for a in rel.get("assets") or []:
            p=_puntua(a.get("name",""),torch_rama,cuda,py_tag)
            if p is not None and p>punt:
                mejor,punt=a.get("browser_download_url"),p
    return (mejor,None) if mejor else (None,i18n.t("catalog.no_wheel",torch=torch_rama,cuda=cuda,python=py_tag))

# Respaldo si PyPI no responde o PyTorch es una nightly sin metadatos.
# No hay formula: 2.10 y 2.11 comparten Triton 3.6, y 2.13 usa 3.7.
TRITON_CONOCIDO={(2,7):(3,3),(2,8):(3,4),(2,9):(3,5),(2,10):(3,6),
                 (2,11):(3,6),(2,12):(3,7),(2,13):(3,7),(2,14):(3,8)}

def _triton_de_torch(torch_version):
    """Rama de Triton que PyTorch declara en PyPI (requisito de su wheel Linux)."""
    m=re.match(r"\d+\.\d+\.\d+",torch_version or "")
    if m:
        try:
            requisitos=_json(f"https://pypi.org/pypi/torch/{m.group(0)}/json")["info"].get("requires_dist") or []
        except (urllib.error.URLError,OSError,ValueError,KeyError):
            requisitos=[]
        for req in requisitos:
            t=re.match(r"triton\s*[=~]=\s*(\d+)\.(\d+)",req)
            if t:
                return int(t.group(1)),int(t.group(2))
    return TRITON_CONOCIDO.get(_version(torch_version))

def regla_triton(torch_version):
    """triton-windows de la misma rama que exige PyTorch, si ya esta publicada."""
    rama=_triton_de_torch(torch_version)
    if not rama:
        return None,i18n.t("catalog.no_safe_rule",torch=torch_version)
    may,men=rama
    try:
        publicadas=_json("https://pypi.org/pypi/triton-windows/json").get("releases",{})
    except (urllib.error.URLError,OSError,ValueError) as e:
        return None,i18n.t("catalog.query_failed",repo="PyPI triton-windows",error=type(e).__name__)
    if not any(re.match(rf"{may}\.{men}\.",k) for k in publicadas):
        return None,i18n.t("catalog.no_safe_rule",torch=torch_version)
    return f"triton-windows>={may}.{men},<{may}.{men+1}",None

def cabeceras_python(carpeta_python,version):
    """Triton compila kernels y necesita include\\ y libs\\ junto a python.exe.

    El Python embebido del portable oficial no los trae; sin ellos Triton
    se importa bien pero falla en el primer kernel. Devuelve (ok, mensaje).
    """
    may,men=version[:2]
    if (os.path.isfile(os.path.join(carpeta_python,"include","Python.h")) and
            os.path.isfile(os.path.join(carpeta_python,"libs",f"python{may}{men}.lib"))):
        return True,None
    try:
        assets=_json(f"https://api.github.com/repos/{CABECERAS_RELEASE}").get("assets") or []
        url=next((a["browser_download_url"] for a in assets
                  if a.get("name","").startswith(f"python_{may}.{men}.")
                  and a["name"].endswith("_include_libs.zip")),None)
        if not url:
            return False,i18n.t("catalog.no_python_headers",version=f"{may}.{men}")
        req=urllib.request.Request(url,headers={"User-Agent":"CineConIA-Installer"})
        with urllib.request.urlopen(req,timeout=TIEMPO_ESPERA) as r:
            datos=r.read()
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            for nombre in z.namelist():
                partes=nombre.replace("\\","/").split("/")
                # Solo include/ y libs/; nunca Lib/ ni rutas que salgan de la carpeta.
                if partes[0] in ("include","libs") and ".." not in partes:
                    z.extract(nombre,carpeta_python)
    except (urllib.error.URLError,OSError,ValueError,KeyError,zipfile.BadZipFile) as e:
        return False,i18n.t("catalog.query_failed",repo="triton-windows include/libs",error=type(e).__name__)
    return True,i18n.t("catalog.python_headers_added",version=f"{may}.{men}")

def plan(herramientas,entorno,py_tag):
    fabricante=entorno.get("fabricante"); torch_rama=entorno.get("torch_rama"); cuda=entorno.get("cuda")
    pasos=[]
    for clave in herramientas:
        h=HERRAMIENTAS[clave]
        p={"clave":clave,"nombre":h["nombre"],"para":h["para"],"licencia":h["licencia"],"url":None,"spec":None,"aviso":None}
        if fabricante not in h.get("fabricantes",{fabricante}):
            p["aviso"]=i18n.t("catalog.not_enabled",vendor=fabricante); pasos.append(p); continue
        if h["fuente"]=="triton":
            p["spec"],p["aviso"]=regla_triton((entorno.get("torch") or {}).get("torch") or torch_rama)
        elif h["fuente"]=="pypi":
            packs=h.get("paquete_por_fabricante")
            p["spec"]=packs.get(fabricante) if packs else h.get("paquete")
        else:
            if fabricante!="nvidia": p["aviso"]=i18n.t("catalog.nvidia_only")
            elif not cuda: p["aviso"]=i18n.t("catalog.cuda_missing")
            else: p["url"],p["aviso"]=buscar_rueda(h["repo"],torch_rama,cuda,py_tag)
        pasos.append(p)
    return pasos
