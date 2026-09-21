"""Catalogo adaptativo de aceleradores."""
from __future__ import annotations
import json, re, urllib.error, urllib.request

TIEMPO_ESPERA = 25
FLAG_ATENCION = "--use-ck-attention"

PERFILES = {
    "h3":{"nombre":"MiniMax H3","detalle":"Video; no descarga el modelo.","herramientas":[],"vram_min":12},
    "wan":{"nombre":"Wan 2.2","detalle":"Video; no descarga el modelo.","herramientas":[],"vram_min":12},
    "ltx":{"nombre":"LTX","detalle":"Video relativamente ligero.","herramientas":[],"vram_min":8},
    "sage":{"nombre":"SageAttention","detalle":"Backend opcional verificado por import.","herramientas":["triton","sageattention"],"vram_min":0},
    "flash":{"nombre":"FlashAttention","detalle":"Backend alternativo para NVIDIA.","herramientas":["flashattention"],"vram_min":0},
    "flux":{"nombre":"Nunchaku","detalle":"Cuantizacion 4-bit para modelos compatibles.","herramientas":["triton","nunchaku"],"vram_min":6},
    "caras":{"nombre":"Retoque de caras","detalle":"InsightFace + ONNX Runtime.","herramientas":["insightface","onnxruntime"],"vram_min":4},
}

HERRAMIENTAS = {
    "triton":{"nombre":"Triton","para":"Runtime para kernels.","fuente":"pypi","paquete":"triton-windows","modulo":"triton","fabricantes":{"nvidia"},
              "spec_por_torch":{"2.7":"triton-windows<3.4","2.8":"triton-windows<3.5","2.9":"triton-windows<3.6","2.10":"triton-windows<3.7"},
              "licencia":"MIT - woct0rdho/triton-windows"},
    "sageattention":{"nombre":"SageAttention 2","para":"Acelera atencion si existe wheel exacta.","fuente":"github","repo":"woct0rdho/SageAttention","modulo":"sageattention","fabricantes":{"nvidia"},"licencia":"Apache-2.0"},
    "flashattention":{"nombre":"FlashAttention","para":"Backend alternativo.","fuente":"github","repo":"kingbri1/flash-attention","modulo":"flash_attn","fabricantes":{"nvidia"},"licencia":"BSD-3-Clause"},
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

def _releases(repo):
    req=urllib.request.Request(f"https://api.github.com/repos/{repo}/releases?per_page=30",
        headers={"Accept":"application/vnd.github+json","User-Agent":"CineConIA-Installer"})
    with urllib.request.urlopen(req,timeout=TIEMPO_ESPERA) as r:
        return json.loads(r.read().decode("utf-8"))

def _puntua(nombre,torch_rama,cuda,py_tag):
    n=(nombre or "").lower()
    if not n.endswith(".whl") or "win_amd64" not in n or not cuda or not torch_rama:
        return None
    may,_,men=cuda.partition("."); men=men or "0"
    if not re.search(rf"cu{re.escape(may)}\.?{re.escape(men)}(?!\d)",n): return None
    t=torch_rama.replace(".","")
    if not re.search(rf"torch{re.escape(torch_rama)}(?!\d)|torch{t}(?!\d)",n): return None
    if "abi3" in n: return 2
    if py_tag.lower() in n: return 3
    if re.search(r"cp\d{2,3}",n): return None
    return 1

def buscar_rueda(repo,torch_rama,cuda,py_tag):
    try: releases=_releases(repo)
    except (urllib.error.URLError,OSError,ValueError) as e:
        return None,f"no se pudo consultar {repo} ({type(e).__name__})"
    mejor,punt=None,-1
    for rel in releases:
        if rel.get("draft") or rel.get("prerelease"): continue
        for a in rel.get("assets") or []:
            p=_puntua(a.get("name",""),torch_rama,cuda,py_tag)
            if p is not None and p>punt:
                mejor,punt=a.get("browser_download_url"),p
    return (mejor,None) if mejor else (None,f"sin wheel para torch {torch_rama} + CUDA {cuda} + {py_tag}")

def plan(herramientas,entorno,py_tag):
    fabricante=entorno.get("fabricante"); torch_rama=entorno.get("torch_rama"); cuda=entorno.get("cuda")
    pasos=[]
    for clave in herramientas:
        h=HERRAMIENTAS[clave]
        p={"clave":clave,"nombre":h["nombre"],"para":h["para"],"licencia":h["licencia"],"url":None,"spec":None,"aviso":None}
        if fabricante not in h.get("fabricantes",{fabricante}):
            p["aviso"]=f"no habilitado para {fabricante}"; pasos.append(p); continue
        if h["fuente"]=="pypi":
            mapa=h.get("spec_por_torch")
            if mapa is not None:
                p["spec"]=mapa.get(torch_rama)
                if not p["spec"]: p["aviso"]=f"sin regla segura para torch {torch_rama}; se omite"
            else:
                packs=h.get("paquete_por_fabricante")
                p["spec"]=packs.get(fabricante) if packs else h.get("paquete")
        else:
            if fabricante!="nvidia": p["aviso"]="solo resuelto para NVIDIA"
            elif not cuda: p["aviso"]="PyTorch no informa CUDA"
            else: p["url"],p["aviso"]=buscar_rueda(h["repo"],torch_rama,cuda,py_tag)
        pasos.append(p)
    return pasos
