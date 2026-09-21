"""Qué instalar y de dónde sacarlo.

Dos ideas sostienen este módulo:

1. Se elige por MODELO, no por herramienta. Nadie se levanta queriendo
   instalar Triton; quiere mover Wan 2.2. El perfil traduce una cosa en la
   otra.

2. Las ruedas se BUSCAN, no se escriben a mano. Una tabla fija de URLs
   caduca en cuanto el autor publica una versión nueva, y cuando la
   combinación del usuario no está en la tabla el instalador se queda
   callado e instala nada. Aquí se consulta la API de releases y, si no
   hay rueda para esa combinación, se dice.
"""
import json
import re
import urllib.error
import urllib.request

TIEMPO_ESPERA = 25


# --- perfiles: lo que el usuario elige ------------------------------------

#: Comfy Kitchen no se instala: viene con ComfyUI como dependencia fijada
#: en su requirements.txt, y se activa con un flag al arrancar.
#:
#: Medido el 2026-09-20 en una RTX 4060 Ti con MiniMax H3, 124 fotogramas y
#: 20 pasos: SageAttention 56,16 s/paso contra ~57,5 de Kitchen. Sage sale
#: un 2-4% más rápido, unos 35 segundos en un render de 19 minutos.
#:
#: Aun así el camino por defecto usa Kitchen: ese 3% se paga con una rueda
#: de terceros que hay que compilar por cada combinación de torch y CUDA, y
#: que para algunas no existe. Quien quiera el 3% marca el perfil "sage".
#: Un instalador que debe funcionar en equipos ajenos cambia un 3% por una
#: dependencia menos sin dudarlo.
FLAG_ATENCION = "--use-ck-attention"

PERFILES = {
    "h3": {
        "nombre": "MiniMax H3  ·  vídeo con audio",
        "detalle": "El flujo completo de Cine con IA. Lo que usa el canal.",
        "herramientas": [],
        "vram_min": 12,
    },
    "wan": {
        "nombre": "Wan 2.2",
        "detalle": "Vídeo de imagen a vídeo y de texto a vídeo.",
        "herramientas": [],
        "vram_min": 12,
    },
    "ltx": {
        "nombre": "LTX-2.5",
        "detalle": "Vídeo rápido, menos exigente de memoria.",
        "herramientas": [],
        "vram_min": 8,
    },
    "hunyuan": {
        "nombre": "HunyuanVideo 1.5",
        "detalle": "Vídeo de Tencent.",
        "herramientas": [],
        "vram_min": 12,
    },
    "sage": {
        "nombre": "SageAttention",
        "detalle": ("Un 2-4% más rápido que la atención que ya trae ComfyUI. "
                    "Hay que compilarlo aparte y no existe rueda para todas "
                    "las combinaciones; si falta, se sigue sin él."),
        "herramientas": ["triton", "sageattention"],
        "vram_min": 0,
    },
    "flash": {
        "nombre": "FlashAttention  ·  opcional",
        "detalle": ("Un tercer backend de atención, con su propio flag de "
                    "arranque. Sin medir en este equipo."),
        "herramientas": ["flashattention"],
        "vram_min": 0,
    },
    "flux": {
        "nombre": "Flux e imagen en 4 bits",
        "detalle": "Nunchaku (SVDQuant) para mover modelos grandes con poca VRAM.",
        "herramientas": ["triton", "nunchaku"],
        "vram_min": 6,
    },
    "caras": {
        "nombre": "Retoque de caras",
        "detalle": "InsightFace y onnxruntime, para reactor y similares.",
        "herramientas": ["insightface", "onnxruntime"],
        "vram_min": 4,
    },
}


# --- herramientas: cómo se instala cada una -------------------------------
#
# "pypi"   -> pip lo resuelve solo, con la restricción que indique 'spec'
# "github" -> hay que buscar la rueda entre los releases de un repositorio

HERRAMIENTAS = {
    "triton": {
        "nombre": "Triton",
        "para": "Compila los kernels que necesita SageAttention.",
        "fuente": "pypi",
        "paquete": "triton-windows",
        # Cada torch quiere su rama de triton. Fuera de este mapa no se
        # inventa nada: se avisa y se sigue.
        "spec_por_torch": {
            "2.7": "triton-windows<3.4",
            "2.8": "triton-windows<3.5",
            "2.9": "triton-windows<3.6",
            "2.10": "triton-windows<3.7",
        },
        "licencia": "MIT  ·  woct0rdho/triton-windows",
    },
    "sageattention": {
        "nombre": "SageAttention 2",
        "para": "Acelera la atención. Es la mejora más grande en vídeo.",
        "fuente": "github",
        "repo": "woct0rdho/SageAttention",
        "modulo": "sageattention",
        "licencia": "Apache-2.0  ·  woct0rdho/SageAttention",
    },
    "flashattention": {
        "nombre": "FlashAttention",
        "para": "Backend de atención alternativo, con su propio flag.",
        "fuente": "github",
        "repo": "kingbri1/flash-attention",
        "modulo": "flash_attn",
        "licencia": "BSD-3-Clause  ·  Dao-AILab/flash-attention",
    },
    "nunchaku": {
        "nombre": "Nunchaku (SVDQuant)",
        "para": "Cuantiza a 4 bits para mover modelos grandes con poca VRAM.",
        "fuente": "github",
        "repo": "nunchux-ai/nunchaku",
        "modulo": "nunchaku",
        "licencia": "Apache-2.0  ·  nunchux-ai/nunchaku",
    },
    "insightface": {
        "nombre": "InsightFace",
        "para": "Detección y análisis de caras.",
        "fuente": "pypi",
        "paquete": "insightface",
        "modulo": "insightface",
        "licencia": "MIT  ·  deepinsight/insightface",
    },
    "onnxruntime": {
        "nombre": "onnxruntime-gpu",
        "para": "Ejecuta los modelos ONNX en la GPU.",
        "fuente": "pypi",
        "paquete": "onnxruntime-gpu",
        "modulo": "onnxruntime",
        "licencia": "MIT  ·  microsoft/onnxruntime",
    },
}


def herramientas_de(perfiles):
    """Las herramientas de varios perfiles, sin repetir y en orden estable.

    El orden importa: Triton antes que SageAttention, porque la segunda lo
    necesita para compilar.
    """
    vistas, salida = set(), []
    for clave in perfiles:
        for h in PERFILES.get(clave, {}).get("herramientas", []):
            if h not in vistas:
                vistas.add(h)
                salida.append(h)
    orden = list(HERRAMIENTAS)
    return sorted(salida, key=orden.index)


# --- resolución de ruedas -------------------------------------------------

def _releases(repo):
    url = f"https://api.github.com/repos/{repo}/releases?per_page=30"
    pet = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "CineConIA-Installer",
    })
    with urllib.request.urlopen(pet, timeout=TIEMPO_ESPERA) as r:
        return json.loads(r.read().decode("utf-8"))


def _puntua(nombre, torch_rama, cuda, py_tag):
    """Cuánto encaja un nombre de rueda con este equipo. None = no vale.

    Se exige coincidencia de CUDA y de torch; la de Python solo cuando el
    nombre trae una etiqueta concreta (cp312) en vez de una genérica
    (abi3, que vale para varias).
    """
    n = nombre.lower()
    if not n.endswith(".whl") or "win_amd64" not in n:
        return None

    # Cada proyecto escribe la versión de CUDA a su manera: woct0rdho usa
    # "cu128" y nunchaku usa "cu12.8". Hay que aceptar las dos o se
    # descartan ruedas que sí existen.
    may, _, men = cuda.partition(".")
    if not re.search(rf"cu{may}\.?{men}(?!\d)", n):
        return None

    # torch2.8.0, torch280 y torch2.8 valen. El (?!\d) evita que "2.1"
    # se dé por bueno dentro de "torch2.10", que es otra versión.
    t = torch_rama.replace(".", "")
    if not re.search(rf"torch{re.escape(torch_rama)}(?!\d)|torch{t}(?!\d)", n):
        return None

    if "abi3" in n:
        return 1            # sirve para cualquier Python 3.x reciente
    if py_tag in n:
        return 2            # compilada justo para este Python
    if re.search(r"cp\d{2,3}", n):
        return None         # es de otro Python
    return 0


def buscar_rueda(repo, torch_rama, cuda, py_tag):
    """La mejor rueda para este equipo, o None con el motivo.

    Devuelve (url, None) si la encuentra, o (None, motivo) si no.
    """
    try:
        releases = _releases(repo)
    except (urllib.error.URLError, OSError, ValueError) as e:
        return None, f"no se pudo consultar {repo} ({type(e).__name__})"

    mejor, mejor_punt = None, -1
    for rel in releases:
        if rel.get("draft"):
            continue
        for a in rel.get("assets") or []:
            p = _puntua(a.get("name", ""), torch_rama, cuda, py_tag)
            if p is not None and p > mejor_punt:
                mejor, mejor_punt = a.get("browser_download_url"), p
    if mejor:
        return mejor, None
    return None, (f"{repo} no publica rueda para torch {torch_rama} + "
                  f"CUDA {cuda} + {py_tag} en Windows")


def plan(herramientas, torch_rama, cuda, py_tag):
    """Qué se instalaría, con su origen resuelto. No instala nada."""
    pasos = []
    for clave in herramientas:
        h = HERRAMIENTAS[clave]
        paso = {"clave": clave, "nombre": h["nombre"], "para": h["para"],
                "licencia": h["licencia"], "url": None, "spec": None, "aviso": None}

        if h["fuente"] == "pypi":
            mapa = h.get("spec_por_torch")
            if mapa:
                paso["spec"] = mapa.get(torch_rama)
                if not paso["spec"]:
                    paso["aviso"] = (f"no hay regla de {h['nombre']} para torch "
                                     f"{torch_rama}; se instalará la última")
                    paso["spec"] = h["paquete"]
            else:
                paso["spec"] = h["paquete"]
        else:
            url, motivo = buscar_rueda(h["repo"], torch_rama, cuda, py_tag)
            paso["url"], paso["aviso"] = url, motivo
        pasos.append(paso)
    return pasos
