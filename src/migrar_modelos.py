"""Migrador seguro de bibliotecas de modelos de ComfyUI.

Siempre simula antes de escribir. Nunca sobrescribe un archivo distinto.
En modo mover: copia, verifica SHA-256 y solo entonces elimina el original.
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

CATEGORIAS = list(modelos_enlace.CARPETAS)
IGNORAR_ARCHIVOS = {"desktop.ini", "thumbs.db", ".ds_store"}
MARCA_INICIO = "# BEGIN CINECONIA MODEL LIBRARY"
MARCA_FIN = "# END CINECONIA MODEL LIBRARY"
BLOQUE_NOMBRE = "cineconia_model_library"
MARGEN_BYTES = 512 * 1024 * 1024


def human_bytes(n):
    n = float(n)
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unidad == "TB":
            return f"{n:.1f} {unidad}"
        n /= 1024
    return f"{n:.1f} TB"


def pedir_si_no(texto, defecto=True):
    sufijo = "[S/n]" if defecto else "[s/N]"
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
    print("\n   No se pudo abrir el selector de Windows.")
    while True:
        ruta = input("   Pega la ruta de la carpeta (Enter cancela): ").strip().strip('"')
        if not ruta:
            return None
        ruta = os.path.abspath(os.path.expandvars(os.path.expanduser(ruta)))
        if os.path.isdir(ruta):
            return ruta
        print("   Esa carpeta no existe.")


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
        if any(os.path.isdir(os.path.join(c, cat)) for cat in CATEGORIAS):
            return os.path.abspath(c)
    return None


def raiz_comfyui_desde_models(models_root):
    padre = os.path.dirname(models_root)
    if os.path.isfile(os.path.join(padre, "main.py")):
        return padre
    return None


def detectar_origenes():
    encontrados = []
    if pedir_si_no("\n¿Buscar bibliotecas de modelos automaticamente?", True):
        print("   Buscando con limites para no recorrer el disco indefinidamente...")
        encontrados = modelos_enlace.detectar_instalaciones(
            profundidad=5, max_directorios=25000, max_resultados=12
        )

    fuentes = []
    if encontrados:
        print("\n   Bibliotecas encontradas:")
        for i, p in enumerate(encontrados, 1):
            print(f"   {i:>2}) {p}")
        print("   T) Todas")
        seleccion = input("\n   Elige numeros separados por coma [T]: ").strip().lower()
        if not seleccion or seleccion == "t":
            fuentes.extend(encontrados)
        else:
            for token in re.split(r"[\s,;]+", seleccion):
                if token.isdigit():
                    idx = int(token) - 1
                    if 0 <= idx < len(encontrados):
                        fuentes.append(encontrados[idx])

    while not fuentes or pedir_si_no("\n¿Agregar otra biblioteca manualmente?", False):
        ruta = seleccionar_carpeta(
            "Selecciona ComfyUI, su carpeta models o una biblioteca de modelos"
        )
        if not ruta:
            if fuentes:
                break
            print("   Debes seleccionar al menos una biblioteca.")
            continue
        models = normalizar_origen(ruta)
        if not models:
            print("   [X] No encontre una carpeta models valida en esa ubicacion.")
            continue
        fuentes.append(models)
        if not pedir_si_no("¿Agregar otra biblioteca?", False):
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
    a = os.path.normcase(os.path.abspath(a))
    b = os.path.normcase(os.path.abspath(b))
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
    raise RuntimeError(f"Demasiados conflictos para {base}")


def iterar_archivos(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d.lower() != "__pycache__"]
        for nombre in files:
            if nombre.lower() in IGNORAR_ARCHIVOS:
                continue
            yield os.path.join(base, nombre)


def construir_plan(fuentes, destino):
    cache = {}
    ocupados = {}
    plan = []
    categorias_lower = {c.lower(): c for c in CATEGORIAS}

    for fuente in fuentes:
        etiqueta = nombre_fuente(fuente)
        for origen in iterar_archivos(fuente):
            rel = os.path.relpath(origen, fuente)
            partes = Path(rel).parts
            primer = partes[0].lower() if partes else ""
            clasificado = primer in categorias_lower
            if clasificado:
                categoria = categorias_lower[primer]
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
    print("  SIMULACION - TODAVIA NO SE HA CAMBIADO NINGUN ARCHIVO")
    print("=" * 68)
    print("\n   Origenes:")
    for p in fuentes:
        print(f"   - {p}")
    print(f"\n   Biblioteca final: {destino}")
    print(f"   Archivos encontrados: {r['total']}")
    print(f"   Datos nuevos:         {human_bytes(r['bytes_nuevos'])}")
    print(f"   Duplicados exactos:   {r['duplicados']}")
    print(f"   Conflictos de nombre: {r['conflictos']}")
    print(f"   Sin clasificar:       {r['sin_clasificar']}")

    muestras = [
        x for x in plan
        if x["accion"] in ("conflicto", "duplicado") or not x["clasificado"]
    ][:20]
    if muestras:
        print("\n   Muestras que requieren atencion:")
        for x in muestras:
            print(f"   [{x['accion']}] {x['origen']}")
            print(f"       -> {x['destino']}")

    print("\n   Se crearan las carpetas estandar de ComfyUI y _sin_clasificar.")


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
    if modo == "copiar":
        return sum(x["tamano"] for x in nuevos) + MARGEN_BYTES

    drive_dest = os.path.splitdrive(os.path.abspath(destino))[0].lower()
    cruzan = 0
    mismo_disco = []
    for x in nuevos:
        drive_src = os.path.splitdrive(os.path.abspath(x["origen"]))[0].lower()
        if not drive_src or not drive_dest or drive_src != drive_dest:
            cruzan += x["tamano"]
        else:
            mismo_disco.append(x["tamano"])
    temporal = max(mismo_disco) if mismo_disco else 0
    return cruzan + temporal + MARGEN_BYTES


def comprobar_espacio(plan, destino, modo):
    try:
        libre = shutil.disk_usage(ancestro_existente(destino)).free
    except OSError:
        print("   [!] No pude calcular espacio libre.")
        return True
    requerido = espacio_requerido(plan, destino, modo)
    print(f"\n   Espacio libre en destino:  {human_bytes(libre)}")
    print(f"   Estimacion prudente:       {human_bytes(requerido)}")
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
        if sha256(origen, cache) != sha256(temporal, {}):
            raise IOError("SHA-256 diferente despues de copiar")

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


def ejecutar_plan(plan, modo, cache):
    total = len(plan)
    resultado = {
        "copiados": 0,
        "eliminados_origen": 0,
        "duplicados": 0,
        "conflictos": 0,
        "errores": [],
    }

    for i, item in enumerate(plan, 1):
        origen = item["origen"]
        destino = item["destino"]
        print(f"\n   [{i}/{total}] {os.path.basename(origen)}")
        try:
            if item["accion"] == "duplicado":
                if not os.path.exists(destino) or not mismo_contenido(origen, destino, cache):
                    raise IOError("el duplicado previsto ya no coincide con el destino")
                resultado["duplicados"] += 1
                if modo == "mover":
                    os.remove(origen)
                    resultado["eliminados_origen"] += 1
                print("      duplicado exacto verificado")
                continue

            final, estado = copiar_verificar(origen, destino, cache)
            if estado == "duplicado":
                resultado["duplicados"] += 1
            else:
                resultado["copiados"] += 1
                if item["accion"] == "conflicto" or "__conflicto_" in os.path.basename(final):
                    resultado["conflictos"] += 1

            if modo == "mover":
                os.remove(origen)
                resultado["eliminados_origen"] += 1
            print(f"      OK -> {final}")

        except Exception as e:
            resultado["errores"].append({
                "origen": origen,
                "destino": destino,
                "error": f"{type(e).__name__}: {e}",
            })
            print(f"      [X] {type(e).__name__}: {e}")

    return resultado


def bloque_yaml(destino):
    base = json.dumps(destino.replace("\\", "/"), ensure_ascii=False)
    lineas = [
        MARCA_INICIO,
        f"{BLOQUE_NOMBRE}:",
        f"    base_path: {base}",
    ]
    for c in CATEGORIAS:
        lineas.append(f"    {c}: {c}")
    lineas.append(MARCA_FIN)
    return "\n".join(lineas)


def actualizar_yaml(comfy_root, destino):
    ruta = os.path.join(comfy_root, "extra_model_paths.yaml")
    previo = ""
    backup = None
    if os.path.isfile(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            previo = f.read()
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = ruta + f".bak-{marca}"
        shutil.copy2(ruta, backup)

    nuevo_bloque = bloque_yaml(destino)
    patron = re.compile(
        re.escape(MARCA_INICIO) + r".*?" + re.escape(MARCA_FIN),
        flags=re.DOTALL,
    )
    if patron.search(previo):
        nuevo = patron.sub(nuevo_bloque, previo)
    else:
        separador = "" if not previo else ("\n" if previo.endswith("\n") else "\n\n")
        nuevo = previo + separador + nuevo_bloque + "\n"

    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(nuevo)
    return ruta, backup


def guardar_reporte(destino, fuentes, modo, plan, resultado, yaml_actualizados):
    carpeta = os.path.join(destino, "_cineconia_migracion")
    os.makedirs(carpeta, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
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
    return ruta


def main():
    print("\nMigrador seguro de modelos de ComfyUI")
    print("------------------------------------")
    print("Cierra ComfyUI antes de comenzar.")
    print("Puedes consolidar una o varias bibliotecas en un solo disco.")

    fuentes = detectar_origenes()
    if not fuentes:
        print("\n[X] No se seleccionaron bibliotecas.")
        return 1

    print("\nSelecciona la carpeta PADRE donde quieres guardar la biblioteca.")
    print("Ejemplo: D:\\IA\\Modelos\\ComfyUI")
    print("El migrador creara o usara dentro de ella una carpeta models.")
    seleccion_dest = seleccionar_carpeta("Selecciona la carpeta de destino")
    if not seleccion_dest:
        print("\n[X] No se selecciono destino.")
        return 1
    destino = normalizar_destino(seleccion_dest)

    for fuente in fuentes:
        if rutas_se_solapan(fuente, destino):
            print(f"\n[X] El destino se solapa con el origen: {fuente}")
            print("    Elige una carpeta diferente.")
            return 1

    print("\nModo de migracion:")
    print("   1) Copiar. Conserva todos los originales.")
    print("   2) Mover seguro. Copia, verifica SHA-256 y despues borra el original.")
    modo = "mover" if input("   Elige [1]: ").strip() == "2" else "copiar"

    print("\nConstruyendo simulacion...")
    plan, cache = construir_plan(fuentes, destino)
    if not plan:
        print("[X] No se encontraron archivos para migrar.")
        return 1

    mostrar_simulacion(plan, fuentes, destino)
    if not comprobar_espacio(plan, destino, modo):
        print("\n[X] No hay espacio libre suficiente.")
        print("    No se modifico ningun archivo.")
        return 2

    print("\nPara ejecutar el plan escribe exactamente: MIGRAR")
    if input("   Confirmacion: ").strip() != "MIGRAR":
        print("\nCancelado. No se modifico ningun archivo.")
        return 0

    os.makedirs(destino, exist_ok=True)
    for c in CATEGORIAS + ["_sin_clasificar"]:
        os.makedirs(os.path.join(destino, c), exist_ok=True)

    resultado = ejecutar_plan(plan, modo, cache)

    if modo == "mover":
        for fuente in fuentes:
            limpiar_vacios(fuente)

    yaml_actualizados = []
    roots = []
    vistos = set()
    for fuente in fuentes:
        root = raiz_comfyui_desde_models(fuente)
        if root:
            clave = os.path.normcase(os.path.normpath(root))
            if clave not in vistos:
                vistos.add(clave)
                roots.append(root)

    if roots and pedir_si_no(
        "\n¿Actualizar estas instalaciones de ComfyUI para usar la nueva biblioteca?", True
    ):
        for root in roots:
            try:
                ruta, backup = actualizar_yaml(root, destino)
                yaml_actualizados.append({"comfyui": root, "yaml": ruta, "backup": backup})
                print(f"   OK {ruta}")
                if backup:
                    print(f"      copia de seguridad: {backup}")
            except Exception as e:
                print(f"   [X] {root}: {type(e).__name__}: {e}")

    reporte = guardar_reporte(destino, fuentes, modo, plan, resultado, yaml_actualizados)

    print("\n" + "=" * 68)
    print("  MIGRACION TERMINADA")
    print("=" * 68)
    print(f"   Biblioteca:           {destino}")
    print(f"   Copiados:             {resultado['copiados']}")
    print(f"   Duplicados:           {resultado['duplicados']}")
    print(f"   Conflictos guardados: {resultado['conflictos']}")
    print(f"   Originales borrados:  {resultado['eliminados_origen']}")
    print(f"   Errores:              {len(resultado['errores'])}")
    print(f"   Reporte:              {reporte}")
    print("\n   Lo no clasificable queda en _sin_clasificar.")
    if resultado["errores"]:
        print("   Los originales con error NO se borraron.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
