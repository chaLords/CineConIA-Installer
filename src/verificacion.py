"""Prueba de arranque real: sin servidor ni navegador, usando el propio ComfyUI."""
from __future__ import annotations
import os
import re
import i18n
import pasos


def analizar(salida, carpetas):
    """Un codigo 0 de ComfyUI no basta: puede haber fallado un custom node."""
    cargados=set()
    errores=[]
    resumen_importacion=False
    for linea in salida:
        lower=linea.lower()
        if any(texto in lower for texto in ("import failed","cannot import ","failed to import ","could not import ")):
            errores.append(linea.strip())
        if "import times for custom nodes:" in lower:
            resumen_importacion=True
            cargados.clear()
            continue
        m=re.search(r"\bseconds(?:\s+\(IMPORT FAILED\))?:\s+(.+)$",linea)
        # Prestartup scripts usan el mismo formato de tiempos: no prueban que
        # el paquete haya cargado. Solo vale el resumen final de importaciones.
        if resumen_importacion and m and "IMPORT FAILED" not in linea:
            nombre=os.path.basename(m.group(1).strip().replace("\\","/"))
            cargados.add(nombre.casefold())
    faltan=[c for c in carpetas if c.casefold() not in cargados]
    return faltan,errores


def comprobar(destino, py, carpetas, manager=None, restricciones=None):
    raiz=os.path.join(destino,"ComfyUI")
    cli=os.path.join(raiz,"comfy","cli_args.py")
    try:
        with open(cli,encoding="utf-8") as f:
            flags=f.read()
    except OSError as e:
        return False,str(e)
    requeridos=("--quick-test-for-ci","--disable-auto-launch","--disable-all-custom-nodes","--whitelist-custom-nodes")
    if any(flag not in flags for flag in requeridos):
        return False,i18n.t("installer.startup_unsupported")
    cmd=[py,"-s",os.path.join(raiz,"main.py"),"--quick-test-for-ci",
         "--disable-auto-launch","--disable-all-custom-nodes"]
    if carpetas:
        cmd += ["--whitelist-custom-nodes"]+list(carpetas)
    if manager=="integrado":
        cmd.append("--enable-manager")
    entorno={"PIP_CONSTRAINT":restricciones} if restricciones else None
    ok,salida=pasos.correr(cmd,i18n.t("installer.startup_check"),cwd=raiz,timeout=300,completo=True,entorno=entorno)
    faltan,errores=analizar(salida,carpetas)
    if not ok or faltan or errores:
        detalle="; ".join(errores[-3:] or faltan or salida[-3:])
        return False,detalle or i18n.t("installer.startup_failed")
    return True,i18n.t("installer.startup_ok",count=len(carpetas))
