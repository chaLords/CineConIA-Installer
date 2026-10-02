"""Reutiliza modelos existentes sin copiarlos.

La busqueda tiene limites para que un disco grande no deje el instalador
aparentemente congelado.
"""
from __future__ import annotations
import json
import os
import re
import shutil
import string
from datetime import datetime

CARPETAS=[
    "checkpoints","diffusion_models","unet","text_encoders","clip","clip_vision",
    "vae","loras","controlnet","upscale_models","embeddings","hypernetworks",
    "style_models","gligen","latent_upscale_models","frame_interpolation","vae_approx",
]
# Nombres que usan A1111 / Forge / SD.Next para las mismas categorias.
ALIAS={
    "stable-diffusion":"checkpoints",
    "lora":"loras",
    "lycoris":"loras",
    "esrgan":"upscale_models",
    "realesrgan":"upscale_models",
    "swinir":"upscale_models",
}
IGNORAR={"$recycle.bin","windows","program files","program files (x86)","programdata",
         "appdata","node_modules",".git","system volume information","python_embeded",
         "custom_nodes","venv","site-packages","users"}
MARCA_INICIO="# BEGIN CINECONIA MODEL LIBRARY"
MARCA_FIN="# END CINECONIA MODEL LIBRARY"
BLOQUE_NOMBRE="cineconia_model_library"

def ruta_registro():
    base=os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    return os.path.join(base,"CineConIA","bibliotecas.json")

def bibliotecas_guardadas():
    try:
        with open(ruta_registro(),encoding="utf-8") as f:
            datos=json.load(f)
        rutas=datos.get("bibliotecas",[]) if isinstance(datos,dict) else []
        if not isinstance(rutas,list):
            return []
        return [p for p in rutas if isinstance(p,str) and os.path.isabs(p)]
    except (OSError,ValueError):
        return []

def registrar_biblioteca(models):
    """Preferencia local del usuario: sigue disponible al descargar otro instalador."""
    models=os.path.realpath(models)
    anteriores=[p for p in bibliotecas_guardadas() if os.path.normcase(os.path.realpath(p))!=os.path.normcase(models)]
    ruta=ruta_registro()
    os.makedirs(os.path.dirname(ruta),exist_ok=True)
    temporal=ruta+".part"
    with open(temporal,"w",encoding="utf-8") as f:
        json.dump({"bibliotecas":[models]+anteriores},f,ensure_ascii=False,indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporal,ruta)
    return ruta

def es_central(models):
    clave=os.path.normcase(os.path.realpath(models))
    return (any(os.path.normcase(os.path.realpath(p))==clave for p in bibliotecas_guardadas())
            or os.path.isdir(os.path.join(models,"_cineconia_migracion")))

def categoria_de(nombre_carpeta):
    """Categoria de ComfyUI para una subcarpeta de models, o None."""
    n=nombre_carpeta.lower()
    for c in CARPETAS:
        if c==n:
            return c
    return ALIAS.get(n)

def mapa_categorias(models):
    """{categoria: subcarpeta real} de lo que existe dentro de models."""
    mapa={}
    try: entradas=sorted(os.scandir(models),key=lambda e:e.name.lower())
    except OSError: return mapa
    for e in entradas:
        if not e.is_dir(): continue
        c=categoria_de(e.name)
        if c and (c not in mapa or e.name.lower()==c):
            mapa[c]=e.name
    return mapa

def discos_fijos():
    """Unidades locales fijas (C:, D:, ...), sin USB ni unidades de red."""
    try:
        import ctypes
        k=ctypes.windll.kernel32
        mascara=k.GetLogicalDrives()
        return [f"{l}:/" for i,l in enumerate(string.ascii_uppercase)
                if mascara>>i & 1 and k.GetDriveTypeW(f"{l}:\\")==3]
    except (AttributeError,OSError):
        return [d for d in ("C:/","D:/","E:/") if os.path.isdir(d)]

def detectar_instalaciones(profundidad=5,max_directorios=25000,max_resultados=10):
    candidatos,vistos=[],set()
    for carpeta in bibliotecas_guardadas():
        clave=os.path.normcase(os.path.realpath(carpeta))
        if clave not in vistos and mapa_categorias(carpeta) and len(candidatos)<max_resultados:
            vistos.add(clave)
            candidatos.append(carpeta)
    raices=[os.path.expanduser("~/Documents"),os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads")]+discos_fijos()
    visitados=0
    def mirar(carpeta,nivel):
        nonlocal visitados
        if nivel>profundidad or visitados>=max_directorios: return
        try: entradas=list(os.scandir(carpeta))
        except OSError: return
        visitados+=1
        for e in entradas:
            if len(candidatos)>=max_resultados: return
            try: es_dir=e.is_dir(follow_symlinks=False)
            except OSError: continue
            if not es_dir: continue
            nombre=e.name.lower()
            if nombre in IGNORAR or nombre.startswith("."): continue
            if nombre=="models":
                real=os.path.normpath(e.path)
                clave=os.path.normcase(os.path.realpath(real))
                if clave not in vistos and mapa_categorias(real):
                    vistos.add(clave); candidatos.append(real)
                continue
            mirar(e.path,nivel+1)
    for raiz in raices:
        if len(candidatos)>=max_resultados: break
        if os.path.isdir(raiz): mirar(raiz,1)
    return candidatos

def tamano_gb(carpeta):
    return round(tamano_bytes(carpeta)/1e9,1)

def tamano_bytes(carpeta):
    total=0
    for sub in mapa_categorias(carpeta).values():
        for raiz,_,archivos in os.walk(os.path.join(carpeta,sub)):
            for nombre in archivos:
                try: total+=os.path.getsize(os.path.join(raiz,nombre))
                except OSError: pass
    return total

# Lo que trae cualquier ComfyUI recien instalado: marcadores put_*_here y los
# decodificadores TAESD de vista previa. No es una biblioteca del usuario.
CATEGORIAS_DE_FABRICA={"vae_approx"}

def tiene_modelos(carpeta):
    """True si hay algun modelo propio, no solo lo que trae el portable."""
    for categoria,sub in mapa_categorias(carpeta).items():
        if categoria in CATEGORIAS_DE_FABRICA:
            continue
        for _,_,archivos in os.walk(os.path.join(carpeta,sub)):
            if any(not nombre.startswith("put_") for nombre in archivos):
                return True
    return False

def bloque_yaml(models,mapa=None):
    """Bloque administrado; mapa={categoria: subcarpeta} (por defecto, todas)."""
    mapa=mapa or {c:c for c in CARPETAS}
    base=json.dumps(models.replace("\\","/"),ensure_ascii=False)
    lineas=[MARCA_INICIO,f"{BLOQUE_NOMBRE}:",f"    base_path: {base}"]
    if es_central(models):
        lineas.append("    is_default: true")
    for c in CARPETAS:
        if c in mapa:
            lineas.append(f"    {c}: {json.dumps(mapa[c],ensure_ascii=False)}")
    lineas.append(MARCA_FIN)
    return "\n".join(lineas)

def actualizar_yaml(comfy_root,models,mapa=None,bibliotecas=None):
    """Escribe o reemplaza solo el bloque administrado, con copia .bak previa."""
    ruta=os.path.join(comfy_root,"extra_model_paths.yaml")
    previo,backup="",None
    if os.path.isfile(ruta):
        with open(ruta,"r",encoding="utf-8") as f:
            previo=f.read()
        backup=ruta+datetime.now().strftime(".bak-%Y%m%d-%H%M%S-%f")
        shutil.copy2(ruta,backup)
    nuevo_bloque=bloque_yaml(models,mapa)
    if bibliotecas:
        bloques=[]
        vistas=set()
        for biblioteca in bibliotecas:
            clave=os.path.normcase(os.path.realpath(biblioteca))
            if clave in vistas:
                continue
            vistas.add(clave)
            categorias=mapa_categorias(biblioteca)
            if not categorias:
                raise ValueError('MODEL_LIBRARY_EMPTY: '+biblioteca)
            bloque=bloque_yaml(biblioteca,categorias)
            bloque=bloque.replace(MARCA_INICIO+'\n','').replace('\n'+MARCA_FIN,'')
            bloque=bloque.replace(BLOQUE_NOMBRE+':',BLOQUE_NOMBRE+f'_{len(bloques)+1}:',1)
            bloques.append(bloque)
        nuevo_bloque=MARCA_INICIO+'\n'+'\n'.join(bloques)+'\n'+MARCA_FIN
    patron=re.compile(re.escape(MARCA_INICIO)+r".*?"+re.escape(MARCA_FIN),flags=re.DOTALL)
    if patron.search(previo):
        nuevo=patron.sub(lambda _:nuevo_bloque,previo)
    else:
        separador="" if not previo else ("\n" if previo.endswith("\n") else "\n\n")
        nuevo=previo+separador+nuevo_bloque+"\n"
    temporal=ruta+".cineconia-part"
    with open(temporal,"w",encoding="utf-8",newline="\n") as f:
        f.write(nuevo)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporal,ruta)
    return ruta,backup
