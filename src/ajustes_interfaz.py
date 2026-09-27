"""Ajustes de la interfaz de ComfyUI que deja el instalador.

ComfyUI guarda las preferencias de la interfaz en
ComfyUI/user/default/comfy.settings.json y solo escribe las que el usuario
cambio. Aqui se agregan las que faltan: lo que el usuario ya eligio no se toca.
"""
from __future__ import annotations
import json, os, shutil
from datetime import datetime

# El panel flotante de la cola ("Total", "Nodo actual", en ejecucion/en cola)
# queda encima del lienzo y repite lo que ya muestran la barra de rgthree y el
# nodo Render de Cine con IA. QPOV2 acopla la cola al panel lateral de trabajos;
# ShowRunProgressBar apaga la barra de progreso que la cola acoplada agrega
# arriba. Las dos se vuelven a activar desde el menu "..." de la cola.
AJUSTES={
    "Comfy.Queue.QPOV2":True,
    "Comfy.Queue.ShowRunProgressBar":False,
}

def ruta_ajustes(destino):
    return os.path.join(destino,"ComfyUI","user","default","comfy.settings.json")

def aplicar(destino,ajustes=None):
    """Agrega los ajustes que falten. Devuelve (estado, detalle):
    "ok" con la ruta del respaldo (None si el archivo no existia),
    "igual" si no habia nada que agregar y "error" con el motivo.
    Un archivo que no se puede leer no se toca."""
    ajustes=AJUSTES if ajustes is None else ajustes
    ruta=ruta_ajustes(destino)
    actuales={}
    if os.path.isfile(ruta):
        try:
            with open(ruta,encoding="utf-8-sig") as f:
                actuales=json.load(f)
        except (OSError,ValueError) as e:
            return "error",str(e)
        if not isinstance(actuales,dict):
            return "error",ruta
    faltan={k:v for k,v in ajustes.items() if k not in actuales}
    if not faltan:
        return "igual",None
    backup=None
    temporal=ruta+".cineconia-part"
    try:
        os.makedirs(os.path.dirname(ruta),exist_ok=True)
        if os.path.isfile(ruta):
            backup=ruta+datetime.now().strftime(".bak-%Y%m%d-%H%M%S-%f")
            shutil.copy2(ruta,backup)
        with open(temporal,"w",encoding="utf-8",newline="\n") as f:
            json.dump({**actuales,**faltan},f,indent=4,ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporal,ruta)
    except OSError as e:
        if os.path.exists(temporal):
            try:
                os.remove(temporal)
            except OSError:
                pass
        return "error",str(e)
    return "ok",backup
