"""Migrador seguro de bibliotecas de modelos de ComfyUI.

Siempre simula antes de escribir. Nunca sobrescribe un archivo distinto.
En modo mover: copia toda la operacion, verifica el conjunto con SHA-256 y
solo despues elimina originales, comprobando cada pareja una vez mas.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime

try:
    import modelos_enlace
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import modelos_enlace
import i18n

t=i18n.t

CATEGORIAS = list(modelos_enlace.CARPETAS)
IGNORAR_ARCHIVOS = {"desktop.ini", "thumbs.db", ".ds_store"}
# Marcadores vacios que trae el portable oficial en cada carpeta de models.
PATRON_MARCADOR = re.compile(r"^put_.*_here$", re.IGNORECASE)
MARGEN_BYTES = 512 * 1024 * 1024


def human_bytes(n):
    n = float(n)
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unidad == "TB":
            return f"{n:.1f} {unidad}"
        n /= 1024
    return f"{n:.1f} TB"


def pedir_si_no(texto, defecto=True):
    sufijo = t("migrator.yes_suffix") if defecto else t("migrator.no_suffix")
    while True:
        r = input(f"{texto} {sufijo}: ").strip().lower()
        if not r:
            return defecto
        if r in ("s", "si", "sí", "y", "yes"):
            return True
        if r in ("n", "no"):
            return False


def powershell_folder(title):
    ps = shutil.which("powershell.exe") or shutil.which("powershell")
    if not ps:
        return None
    env = os.environ.copy()
    env["CINECONIA_FOLDER_TITLE"] = title
    script = (
        "$s=New-Object -ComObject Shell.Application;"
        "$f=$s.BrowseForFolder(0,$env:CINECONIA_FOLDER_TITLE,0,0);"
        "if($f){[Console]::OutputEncoding=[Text.UTF8Encoding]::UTF8;"
        "Write-Output $f.Self.Path}"
    )
    try:
        r = subprocess.run(
            [ps, "-NoProfile", "-Sta", "-Command", script],
            capture_output=True, text=True, timeout=300, env=env
        )
    except (OSError, subprocess.SubprocessError):
        return None
    ruta = (r.stdout or "").strip()
    return os.path.abspath(ruta) if ruta else None


def seleccionar_carpeta(titulo):
    ruta = powershell_folder(titulo)
    if ruta:
        return ruta
    print("\n   "+t("migrator.folder_dialog_failed"))
    while True:
        ruta = input("   "+t("migrator.paste_path")).strip().strip('"')
        if not ruta:
            return None
        ruta = os.path.abspath(os.path.expandvars(os.path.expanduser(ruta)))
        if os.path.isdir(ruta):
            return ruta
        print("   "+t("migrator.folder_missing"))


def normalizar_origen(ruta):
    ruta = os.path.abspath(ruta)
    candidatos = [
        ruta,
        os.path.join(ruta, "models"),
        os.path.join(ruta, "ComfyUI", "models"),
    ]
    for c in candidatos:
        if not os.path.isdir(c):
            continue
        if os.path.basename(os.path.normpath(c)).lower() == "models":
            return os.path.abspath(c)
        if modelos_enlace.mapa_categorias(c):
            return os.path.abspath(c)
    return None


def raiz_comfyui_desde_models(models_root):
    padre = os.path.dirname(models_root)
    if os.path.isfile(os.path.join(padre, "main.py")):
        return padre
    return None


def detectar_origenes(encontrados=None):
    """Elige las bibliotecas de origen. Con encontrados, no vuelve a buscar
    (el instalador ya recorrio los discos)."""
    if encontrados is None:
        encontrados = []
        if pedir_si_no("\n"+t("migrator.search"), True):
            print("   "+t("migrator.searching"))
            encontrados = modelos_enlace.detectar_instalaciones(
                profundidad=5, max_directorios=25000, max_resultados=12
            )

    fuentes = []
    if encontrados:
        print("\n   "+t("migrator.found"))
        for i, p in enumerate(encontrados, 1):
            print(f"   {i:>2}) {p}")
        print("   "+t("migrator.all"))
        seleccion = input("\n   "+t("migrator.choose_found")).strip().lower()
        if not seleccion or seleccion in ("t","a"):
            fuentes.extend(encontrados)
        else:
            for token in re.split(r"[\s,;]+", seleccion):
                if token.isdigit():
                    idx = int(token) - 1
                    if 0 <= idx < len(encontrados):
                        fuentes.append(encontrados[idx])

    while not fuentes or pedir_si_no("\n"+t("migrator.add_manual"), False):
        ruta = seleccionar_carpeta(
            t("migrator.select_source")
        )
        if not ruta:
            if fuentes:
                break
            print("   "+t("migrator.need_source"))
            continue
        models = normalizar_origen(ruta)
        if not models:
            print("   "+t("migrator.invalid_source"))
            continue
        fuentes.append(models)
        if not pedir_si_no(t("migrator.add_another"), False):
            break

    unicas = []
    vistos = set()
    for p in fuentes:
        clave = os.path.normcase(os.path.normpath(p))
        if clave not in vistos:
            vistos.add(clave)
            unicas.append(os.path.abspath(p))
    return unicas


def normalizar_destino(seleccion):
    seleccion = os.path.abspath(seleccion)
    if os.path.basename(os.path.normpath(seleccion)).lower() == "models":
        return seleccion
    if any(os.path.isdir(os.path.join(seleccion, c)) for c in CATEGORIAS):
        return seleccion
    return os.path.join(seleccion, "models")


def rutas_se_solapan(a, b):
    a = os.path.normcase(os.path.realpath(a))
    b = os.path.normcase(os.path.realpath(b))
    try:
        comun = os.path.commonpath([a, b])
    except ValueError:
        return False
    return comun == a or comun == b


def sha256(ruta, cache):
    ruta = os.path.abspath(ruta)
    try:
        stat = os.stat(ruta)
        clave = (ruta, stat.st_size, stat.st_mtime_ns)
    except OSError:
        clave = (ruta, None, None)
    if clave in cache:
        return cache[clave]
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        while True:
            bloque = f.read(8 * 1024 * 1024)
            if not bloque:
                break
            h.update(bloque)
    valor = h.hexdigest()
    cache[clave] = valor
    return valor


def mismo_contenido(a, b, cache):
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
    except OSError:
        return False
    return sha256(a, cache) == sha256(b, cache)


def nombre_fuente(models_root):
    padre = os.path.basename(os.path.dirname(models_root)) or "biblioteca"
    seguro = re.sub(r"[^A-Za-z0-9._-]+", "_", padre).strip("_")
    return seguro or "biblioteca"


def destino_conflicto(base, ocupados):
    p = Path(base)
    for n in range(2, 10000):
        candidato = str(p.with_name(f"{p.stem}__conflicto_{n}{p.suffix}"))
        clave = os.path.normcase(os.path.normpath(candidato))
        if clave not in ocupados and not os.path.exists(candidato):
            return candidato
    raise RuntimeError(t("migrator.too_many_conflicts",path=base))


def iterar_archivos(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d.lower() != "__pycache__"]
        for nombre in files:
            if nombre.lower() in IGNORAR_ARCHIVOS or PATRON_MARCADOR.match(nombre):
                continue
            yield os.path.join(base, nombre)


def construir_plan(fuentes, destino):
    cache = {}
    ocupados = {}
    plan = []

    for fuente in fuentes:
        etiqueta = nombre_fuente(fuente)
        for origen in iterar_archivos(fuente):
            rel = os.path.relpath(origen, fuente)
            partes = Path(rel).parts
            categoria = modelos_enlace.categoria_de(partes[0]) if len(partes) > 1 else None
            clasificado = categoria is not None
            if clasificado:
                objetivo = os.path.join(destino, categoria, *partes[1:])
            else:
                categoria = "_sin_clasificar"
                objetivo = os.path.join(destino, categoria, etiqueta, rel)

            clave = os.path.normcase(os.path.normpath(objetivo))
            accion = "copiar"
            destino_final = objetivo

            if os.path.exists(objetivo):
                if mismo_contenido(origen, objetivo, cache):
                    accion = "duplicado"
                else:
                    destino_final = destino_conflicto(objetivo, ocupados)
                    accion = "conflicto"
            elif clave in ocupados:
                previo = ocupados[clave]
                if mismo_contenido(origen, previo, cache):
                    accion = "duplicado"
                else:
                    destino_final = destino_conflicto(objetivo, ocupados)
                    accion = "conflicto"

            if accion != "duplicado":
                ocupados[os.path.normcase(os.path.normpath(destino_final))] = origen

            try:
                tamano = os.path.getsize(origen)
            except OSError:
                tamano = 0
            plan.append({
                "origen": origen,
                "destino": destino_final,
                "accion": accion,
                "tamano": tamano,
                "categoria": categoria,
                "clasificado": clasificado,
            })
    return plan, cache


def resumen_plan(plan):
    return {
        "total": len(plan),
        "duplicados": sum(1 for x in plan if x["accion"] == "duplicado"),
        "conflictos": sum(1 for x in plan if x["accion"] == "conflicto"),
        "sin_clasificar": sum(1 for x in plan if not x["clasificado"]),
        "bytes_nuevos": sum(x["tamano"] for x in plan if x["accion"] != "duplicado"),
    }


def mostrar_simulacion(plan, fuentes, destino):
    r = resumen_plan(plan)
    print("\n" + "=" * 68)
    print("  "+t("migrator.simulation_title"))
    print("=" * 68)
    print("\n   "+t("migrator.sources"))
    for p in fuentes:
        print(f"   - {p}")
    print("\n   "+t("migrator.final_library",path=destino))
    print("   "+t("migrator.files_found",count=r["total"]))
    print("   "+t("migrator.new_data",size=human_bytes(r["bytes_nuevos"])))
    print("   "+t("migrator.exact_duplicates",count=r["duplicados"]))
    print("   "+t("migrator.name_conflicts",count=r["conflictos"]))
    print("   "+t("migrator.unclassified",count=r["sin_clasificar"]))

    muestras = [
        x for x in plan
        if x["accion"] in ("conflicto", "duplicado") or not x["clasificado"]
    ][:20]
    if muestras:
        print("\n   "+t("migrator.samples"))
        for x in muestras:
            print(f"   [{x['accion']}] {x['origen']}")
            print(f"       -> {x['destino']}")

    print("\n   "+t("migrator.standard_folders"))
    print(f"   {destino}")
    for categoria in CATEGORIAS + ["_sin_clasificar"]:
        cantidad=sum(1 for x in plan if x["categoria"]==categoria)
        print(f"     +-- {categoria}/"+(f"  ({cantidad})" if cantidad else ""))
    print("\n   "+t("migrator.shared_library"))


def ancestro_existente(ruta):
    p = os.path.abspath(ruta)
    while not os.path.exists(p):
        padre = os.path.dirname(p)
        if padre == p:
            break
        p = padre
    return p


def espacio_requerido(plan, destino, modo):
    nuevos = [x for x in plan if x["accion"] != "duplicado"]
    # Ambos modos copian TODO antes de borrar: tambien en el mismo disco.
    return sum(x["tamano"] for x in nuevos) + MARGEN_BYTES


def comprobar_espacio(plan, destino, modo):
    try:
        libre = shutil.disk_usage(ancestro_existente(destino)).free
    except OSError:
        print("   "+t("migrator.space_unknown"))
        return False
    requerido = espacio_requerido(plan, destino, modo)
    print("\n   "+t("migrator.space_free",size=human_bytes(libre)))
    print("   "+t("migrator.space_estimate",size=human_bytes(requerido)))
    return libre >= requerido


def copiar_verificar(origen, destino, cache):
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    final = destino
    if os.path.exists(final):
        if mismo_contenido(origen, final, cache):
            return final, "duplicado"
        final = destino_conflicto(final, {os.path.normcase(os.path.normpath(final))})

    temporal = final + ".cineconia-part"
    try:
        if os.path.exists(temporal):
            os.remove(temporal)
        shutil.copy2(origen, temporal)
        with open(temporal,"rb+") as archivo:
            os.fsync(archivo.fileno())
        if sha256(origen, {}) != sha256(temporal, {}):
            raise IOError(t("migrator.hash_mismatch"))

        if os.path.exists(final):
            if mismo_contenido(origen, final, cache):
                os.remove(temporal)
                return final, "duplicado"
            final = destino_conflicto(final, {os.path.normcase(os.path.normpath(final))})
        os.replace(temporal, final)
        return final, "copiado"
    except Exception:
        try:
            if os.path.exists(temporal):
                os.remove(temporal)
        except OSError:
            pass
        raise


def limpiar_vacios(root):
    for base, dirs, files in os.walk(root, topdown=False):
        if os.path.normcase(base) == os.path.normcase(root):
            continue
        try:
            if not os.listdir(base):
                os.rmdir(base)
        except OSError:
            pass


def ejecutar_plan(plan, modo, cache, antes_de_borrar=None):
    total = len(plan)
    resultado = {
        "copiados": 0,
        "eliminados_origen": 0,
        "duplicados": 0,
        "conflictos": 0,
        "errores": [],
        "archivos": [],
    }
    # Fase 1: copiar y verificar toda la biblioteca. Nunca borrar aqui.
    print("\n"+t("migrator.copy_phase" if modo=="mover" else "migrator.copy_only_phase"))
    for i, item in enumerate(plan, 1):
        origen = item["origen"]
        destino = item["destino"]
        print(f"\n   [{i}/{total}] {os.path.basename(origen)}")
        try:
            if rutas_se_solapan(origen,destino):
                raise IOError(t("migrator.overlap",path=origen))
            if item["accion"] == "duplicado":
                if not os.path.exists(destino) or not mismo_contenido(origen, destino, {}):
                    raise IOError(t("migrator.duplicate_changed"))
                resultado["duplicados"] += 1
                resultado["archivos"].append({"origen":origen,"destino":destino,"estado":"duplicado"})
                print("      "+t("migrator.duplicate_verified"))
                continue
            final, estado = copiar_verificar(origen, destino, {})
            if estado == "duplicado":
                resultado["duplicados"] += 1
            else:
                resultado["copiados"] += 1
                if item["accion"] == "conflicto" or "__conflicto_" in os.path.basename(final):
                    resultado["conflictos"] += 1

            resultado["archivos"].append({"origen":origen,"destino":final,"estado":estado})
            print(f"      OK -> {final}")

        except Exception as e:
            resultado["errores"].append({
                "origen": origen,
                "destino": destino,
                "error": f"{type(e).__name__}: {e}",
            })
            print(f"      [X] {type(e).__name__}: {e}")

    if modo!="mover":
        return resultado
    if resultado["errores"]:
        print("\n"+t("migrator.all_originals_kept"))
        return resultado
    # Fase 2: comprobar de nuevo todas las parejas, sin caches del plan.
    print("\n"+t("migrator.verify_phase"))
    for item in resultado["archivos"]:
        try:
            digest=sha256(item["origen"],{})
            if digest!=sha256(item["destino"],{}):
                raise IOError(t("migrator.hash_mismatch"))
            item["sha256"]=digest
        except OSError as e:
            resultado["errores"].append({**item,"error":str(e)})
    if resultado["errores"]:
        print("\n"+t("migrator.all_originals_kept"))
        return resultado
    # Registrar los destinos y sus hashes antes de eliminar cualquier origen.
    if antes_de_borrar:
        try:
            antes_de_borrar(resultado)
        except OSError as e:
            resultado["errores"].append({"error":str(e)})
            print("\n"+t("migrator.all_originals_kept"))
            return resultado
    # Fase 3: cada origen se borra solo si ambas copias aun coinciden.
    print("\n"+t("migrator.delete_phase"))
    for item in resultado["archivos"]:
        try:
            if (sha256(item["origen"],{})!=item["sha256"] or
                    sha256(item["destino"],{})!=item["sha256"]):
                raise IOError(t("migrator.hash_mismatch"))
            os.remove(item["origen"])
            item["original_eliminado"]=True
            resultado["eliminados_origen"]+=1
        except OSError as e:
            resultado["errores"].append({**item,"error":str(e)})
            break
    return resultado


def guardar_reporte(destino, fuentes, modo, plan, resultado, yaml_actualizados):
    carpeta = os.path.join(destino, "_cineconia_migracion")
    os.makedirs(carpeta, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    ruta = os.path.join(carpeta, f"migracion-{marca}.json")
    data = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "fuentes": fuentes,
        "destino": destino,
        "modo": modo,
        "resumen_plan": resumen_plan(plan),
        "resultado": resultado,
        "extra_model_paths_actualizados": yaml_actualizados,
    }
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    return ruta


def main(encontrados=None, instalaciones_extra=()):
    """encontrados: bibliotecas ya detectadas (desde el instalador).
    instalaciones_extra: raices de ComfyUI que tambien deben apuntar a la
    biblioteca final aunque no sean origen, como la recien instalada."""
    print("\n"+t("migrator.title"))
    print("------------------------------------")
    print(t("migrator.close_comfy"))
    print(t("migrator.consolidate"))

    fuentes = detectar_origenes(encontrados)
    if not fuentes:
        print("\n"+t("migrator.no_sources"))
        return 1

    print("\n"+t("migrator.select_parent"))
    print(t("migrator.destination_example"))
    print(t("migrator.destination_models"))
    seleccion_dest = seleccionar_carpeta(t("migrator.select_destination"))
    if not seleccion_dest:
        print("\n"+t("migrator.no_destination"))
        return 1
    destino = normalizar_destino(seleccion_dest)

    for fuente in fuentes:
        if rutas_se_solapan(fuente, destino):
            print("\n"+t("migrator.overlap",path=fuente))
            print("    "+t("migrator.choose_different"))
            return 1

    print("\n"+t("migrator.mode"))
    print("   "+t("migrator.copy_mode"))
    print("   "+t("migrator.move_mode"))
    modo = "mover" if input("   "+t("migrator.choose_mode")).strip() == "2" else "copiar"

    print("\n"+t("migrator.building"))
    plan, cache = construir_plan(fuentes, destino)
    if not plan:
        print(t("migrator.no_files"))
        return 1

    mostrar_simulacion(plan, fuentes, destino)
    if not comprobar_espacio(plan, destino, modo):
        print("\n"+t("migrator.no_space"))
        print("    "+t("migrator.no_changes_made"))
        return 2

    word=t("migrator.confirm_word")
    print("\n"+t("migrator.confirm",word=word))
    if input("   "+t("migrator.confirm_prompt")).strip() != word:
        print("\n"+t("migrator.cancelled"))
        return None

    os.makedirs(destino, exist_ok=True)
    for c in CATEGORIAS + ["_sin_clasificar"]:
        os.makedirs(os.path.join(destino, c), exist_ok=True)

    resultado = ejecutar_plan(plan, modo, cache, antes_de_borrar=lambda estado:
        guardar_reporte(destino,fuentes,modo,plan,estado,[]))

    if not resultado["errores"]:
        try:
            modelos_enlace.registrar_biblioteca(destino)
            print("\n"+t("migrator.library_remembered",path=destino))
        except OSError as e:
            resultado["errores"].append({"registro":destino,"error":str(e)})

    if modo == "mover":
        for fuente in fuentes:
            limpiar_vacios(fuente)

    yaml_actualizados = []
    roots = []
    vistos = set()
    for root in [raiz_comfyui_desde_models(f) for f in fuentes] + list(instalaciones_extra):
        if root:
            clave = os.path.normcase(os.path.normpath(root))
            if clave not in vistos:
                vistos.add(clave)
                roots.append(root)

    if not resultado["errores"] and roots and pedir_si_no(
        "\n"+t("migrator.update_comfy"), True
    ):
        for root in roots:
            try:
                ruta, backup = modelos_enlace.actualizar_yaml(root, destino)
                yaml_actualizados.append({"comfyui": root, "yaml": ruta, "backup": backup})
                print(f"   OK {ruta}")
                if backup:
                    print("      "+t("migrator.backup",path=backup))
            except Exception as e:
                print(f"   [X] {root}: {type(e).__name__}: {e}")
                resultado["errores"].append({"comfyui":root,"error":str(e)})

    reporte = guardar_reporte(destino, fuentes, modo, plan, resultado, yaml_actualizados)

    print("\n" + "=" * 68)
    print("  "+t("migrator.finished"))
    print("=" * 68)
    print("   "+t("migrator.library",path=destino))
    print("   "+t("migrator.copied",count=resultado["copiados"]))
    print("   "+t("migrator.duplicates",count=resultado["duplicados"]))
    print("   "+t("migrator.conflicts",count=resultado["conflictos"]))
    print("   "+t("migrator.deleted",count=resultado["eliminados_origen"]))
    print("   "+t("migrator.errors",count=len(resultado["errores"])))
    print("   "+t("migrator.report",path=reporte))
    print("\n   "+t("migrator.unclassified_note"))
    if resultado["errores"]:
        print("   "+t("migrator.errors_kept"))
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
