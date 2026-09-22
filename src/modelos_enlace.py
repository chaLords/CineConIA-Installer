"""Reutiliza modelos existentes sin copiarlos.

La busqueda tiene limites para que un disco grande no deje el instalador
aparentemente congelado.
"""
from __future__ import annotations
import os
import i18n

CARPETAS=[
    "checkpoints","diffusion_models","unet","text_encoders","clip","clip_vision",
    "vae","loras","controlnet","upscale_models","embeddings","hypernetworks",
    "style_models","gligen","latent_upscale_models","frame_interpolation","vae_approx",
]
IGNORAR={"$recycle.bin","windows","program files","program files (x86)","programdata",
         "appdata","node_modules",".git","system volume information","python_embeded",
         "custom_nodes","venv","site-packages","users"}

def detectar_instalaciones(profundidad=5,max_directorios=25000,max_resultados=10):
    candidatos,vistos=[],set()
    raices=[os.path.expanduser("~/Documents"),os.path.expanduser("~/Desktop"),"C:/","D:/","E:/"]
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
                if real not in vistos and any(os.path.isdir(os.path.join(real,c)) for c in CARPETAS):
                    vistos.add(real); candidatos.append(real)
                continue
            mirar(e.path,nivel+1)
    for raiz in raices:
        if len(candidatos)>=max_resultados: break
        if os.path.isdir(raiz): mirar(raiz,1)
    return candidatos

def tamano_gb(carpeta):
    total=0
    for categoria in CARPETAS:
        inicio=os.path.join(carpeta,categoria)
        if not os.path.isdir(inicio): continue
        for raiz,_,archivos in os.walk(inicio):
            for nombre in archivos:
                try: total+=os.path.getsize(os.path.join(raiz,nombre))
                except OSError: pass
    return round(total/1e9,1)

def escribir_yaml(destino_comfyui,carpeta_modelos):
    ruta=os.path.join(destino_comfyui,"extra_model_paths.yaml")
    if os.path.exists(ruta): return None,i18n.t("models.yaml_exists",path=ruta)
    base=carpeta_modelos.replace("\\","/")
    lineas=[
        i18n.t("models.yaml_comment"),
        i18n.t("models.yaml_comment2"),
        "otra_instalacion:",
        f"    base_path: {base}",
        "",
    ]
    for c in CARPETAS:
        if os.path.isdir(os.path.join(carpeta_modelos,c)): lineas.append(f"    {c}: {c}")
    try:
        with open(ruta,"w",encoding="utf-8") as f: f.write("\n".join(lineas)+"\n")
    except OSError as e: return None,str(e)
    return ruta,None
