"""Menú del instalador. Detecta, propone, deja elegir y verifica.

La regla de este archivo: nada se instala sin haberlo enseñado antes. El
usuario ve el plan completo —qué, de dónde y con qué licencia— y confirma.
Un instalador que actúa sin decir lo que hace es indistinguible de un
programa que no sabes qué te metió.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalogo  # noqa: E402
import deteccion  # noqa: E402
import modelos_enlace  # noqa: E402
import rutas_largas  # noqa: E402

CANAL = "https://www.youtube.com/@cineconia.oficial"
NODOS_REPO = "https://github.com/chaLords/ComfyUI-Cine-con-IA.git"

A, G, R, X = "\033[38;5;179m", "\033[38;5;245m", "\033[38;5;203m", "\033[0m"


def _consola_utf8():
    """Sin esto los acentos salen como basura en la consola de Windows."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def titulo(t):
    print(f"\n{A}{'=' * 62}\n  {t}\n{'=' * 62}{X}")


def preguntar(texto, opciones, por_defecto=None):
    """Un número entre 1 y N. Enter acepta el valor por defecto."""
    for i, (etq, extra) in enumerate(opciones, 1):
        marca = f" {A}(recomendado){X}" if por_defecto == i else ""
        print(f"   {i}) {etq}{marca}")
        if extra:
            print(f"      {G}{extra}{X}")
    while True:
        d = f" [{por_defecto}]" if por_defecto else ""
        r = input(f"\n   {texto}{d}: ").strip()
        if not r and por_defecto:
            return por_defecto
        if r.isdigit() and 1 <= int(r) <= len(opciones):
            return int(r)
        print(f"   {R}Escribe un número del 1 al {len(opciones)}.{X}")


def marcar(texto, opciones):
    """Varias opciones a la vez: '1,3' o '1 3'. Enter = ninguna."""
    for i, (etq, extra) in enumerate(opciones, 1):
        print(f"   {i}) {etq}")
        if extra:
            print(f"      {G}{extra}{X}")
    r = input(f"\n   {texto} (ej. 1,3  ·  Enter para ninguna): ").strip()
    if not r:
        return []
    nums = [x for x in r.replace(",", " ").split() if x.isdigit()]
    return [int(n) for n in nums if 1 <= int(n) <= len(opciones)]


def mostrar_equipo(inf):
    titulo("Tu equipo")
    d = inf["driver"]
    if d:
        print(f"   GPU        {d['gpu']}  ·  {d['vram_gb']} GB")
        print(f"   Driver     {d['version']}")
    else:
        print(f"   {R}No se detectó una GPU NVIDIA.{X}")
    if inf["arquitectura"]:
        print(f"   Familia    {inf['arquitectura']}")
    if inf["torch"]:
        t = inf["torch"]
        print(f"   PyTorch    {t['torch']}  ·  CUDA {t['cuda']}")
    print(f"   Sistema    {inf['so']}  ·  Python {inf['python']}")
    print(f"   Espacio    {inf['espacio_gb']} GB libres")


def elegir_cuda(inf):
    titulo("Rama de CUDA")
    rec, motivo, disp = inf["cuda_recomendada"], inf["cuda_motivo"], inf["cuda_disponibles"]
    if not disp:
        print(f"   {R}{motivo}{X}")
        return None
    print(f"   {G}{motivo}{X}\n")
    print(f"   {G}CUDA no es un acelerador: no hace tu tarjeta más rápida.")
    print(f"   Lo que cambia entre ramas es cuántas ruedas compiladas existen.{X}\n")
    opciones = [(f"CUDA {c}", None) for c in disp]
    idx = disp.index(rec) + 1 if rec in disp else 1
    return disp[preguntar("Elige la rama", opciones, idx) - 1]


def elegir_perfiles(vram_gb):
    titulo("¿Qué vas a mover?")
    print(f"   {G}Elige por modelo. El instalador deduce qué hace falta.{X}\n")
    claves = list(catalogo.PERFILES)
    opciones = []
    for c in claves:
        p = catalogo.PERFILES[c]
        aviso = ""
        if vram_gb and p["vram_min"] > vram_gb:
            aviso = f"   {R}[pide ~{p['vram_min']} GB y tienes {vram_gb}]{X}"
        opciones.append((p["nombre"] + aviso, p["detalle"]))
    return [claves[i - 1] for i in marcar("Marca los que quieras", opciones)]


def mostrar_plan(pasos):
    titulo("Esto es lo que se va a instalar")
    hay_aviso = False
    for p in pasos:
        print(f"\n   {A}{p['nombre']}{X}")
        print(f"      {G}{p['para']}{X}")
        if p["url"]:
            print(f"      rueda: {os.path.basename(p['url'])}")
        elif p["spec"]:
            print(f"      pip:   {p['spec']}")
        if p["aviso"]:
            hay_aviso = True
            print(f"      {R}AVISO: {p['aviso']}{X}")
        print(f"      {G}licencia: {p['licencia']}{X}")
    if hay_aviso:
        print(f"\n   {R}Lo marcado con AVISO no se instalará: no existe una")
        print(f"   versión compilada para tu combinación exacta. No se fuerza")
        print(f"   una que no encaje, que es como se rompen las instalaciones.{X}")
    return hay_aviso


def pip(py, args, titulo_paso):
    print(f"\n{A}>> {titulo_paso}{X}")
    cmd = [py, "-s", "-m", "pip", "install", "--no-cache-dir",
           "--no-warn-script-location", "--timeout", "600", "--retries", "5"] + args
    return subprocess.run(cmd).returncode == 0


def ejecutar(pasos, py):
    """Instala lo que se pueda. Lo opcional que falle no es un error.

    Devuelve (hechos, fallidos, omitidos). Los omitidos son piezas
    opcionales sin rueda para este equipo: se informan, no se dramatizan,
    y el instalador sigue adelante.
    """
    titulo("Instalando")
    hechos, fallidos, omitidos = [], [], []
    for p in pasos:
        opcional = p["clave"] in OPCIONALES
        if p["aviso"] and not p["url"] and not p["spec"]:
            (omitidos if opcional else fallidos).append((p["nombre"], p["aviso"]))
            continue
        destino = [p["url"]] if p["url"] else [p["spec"]]
        if pip(py, destino, p["nombre"]):
            hechos.append(p)
        else:
            motivo = "pip devolvió error"
            (omitidos if opcional else fallidos).append((p["nombre"], motivo))
    return hechos, fallidos, omitidos


def verificar(pasos, py):
    """Importar lo instalado. Instalar no es lo mismo que funcionar."""
    titulo("Verificación")
    for p in pasos:
        mod = catalogo.HERRAMIENTAS[p["clave"]].get("modulo")
        if not mod:
            continue
        r = subprocess.run(
            [py, "-s", "-c",
             f"import {mod}; print(getattr({mod}, '__version__', 'sin versión'))"],
            capture_output=True, text=True)
        if r.returncode == 0:
            print(f"   {A}OK{X}   {p['nombre']:22} {r.stdout.strip()}")
        else:
            linea = (r.stderr.strip().splitlines() or ["error"])[-1]
            print(f"   {R}FALLA{X} {p['nombre']:22} {linea[:70]}")


#: El paquete se ha distribuido con varios nombres de carpeta. Hay que
#: reconocerlos todos: clonar con un nombre cuando ya existe con otro deja
#: dos copias y ComfyUI registra los nodos por duplicado.
NOMBRES_NODOS = ["ComfyUI-Cine-con-IA", "ComfyUI-CineConIA", "cine-con-ia"]


def instalar_nodos(destino):
    titulo("Nodos Cine con IA")
    custom = os.path.join(destino, "ComfyUI", "custom_nodes")
    for nombre in NOMBRES_NODOS:
        ya = os.path.join(custom, nombre)
        if os.path.isdir(ya):
            print(f"   Ya están instalados en '{nombre}'.")
            return
    if preguntar("¿Instalar los nodos de Cine con IA?",
                 [("Sí", "Los 9 nodos, interfaz en español"), ("No", None)], 1) != 1:
        return
    carpeta = os.path.join(custom, NOMBRES_NODOS[0])
    r = subprocess.run(["git", "clone", "--depth", "1", NODOS_REPO, carpeta])
    if r.returncode == 0:
        print(f"   {A}Instalados.{X} Aparecen en ComfyUI bajo 'Cine con IA'.")
    else:
        print(f"   {R}No se pudo clonar. ¿Tienes git instalado?{X}")


def ofrecer_enlace_modelos(destino):
    """Reutilizar modelos que ya estén en el disco, en vez de rebajarlos.

    Solo se pregunta si de verdad hay algo que enlazar. Si no se encuentra
    ninguna otra instalación, el usuario ni se entera de que esto existe.
    """
    destino_comfy = os.path.join(destino, "ComfyUI")
    propia = os.path.normpath(os.path.join(destino_comfy, "models"))
    encontradas = [c for c in modelos_enlace.detectar_instalaciones()
                   if os.path.normpath(c) != propia]
    if not encontradas:
        return

    titulo("Modelos que ya tienes")
    print(f"   {G}Este instalador no descarga modelos. Pero he encontrado")
    print(f"   estos en tu disco: se pueden usar sin copiar ni mover nada.{X}\n")
    opciones = []
    for c in encontradas[:5]:
        opciones.append((f"{modelos_enlace.tamano_gb(c):.1f} GB  ·  {c}", None))
    opciones.append(("No enlazar nada", "Empezar con la carpeta vacía"))

    elegida = preguntar("¿Cuál uso?", opciones, 1)
    if elegida > len(encontradas[:5]):
        return
    ruta, error = modelos_enlace.escribir_yaml(destino_comfy, encontradas[elegida - 1])
    if ruta:
        print(f"   {A}Enlazados.{X} ComfyUI los verá como suyos.")
        print(f"   {G}Escrito en {os.path.basename(ruta)}; no se copió ni un byte.{X}")
    else:
        print(f"   {G}No se escribió nada: {error}{X}")


#: Lo que se instala si el usuario no toca nada. Es el caso del 95%:
#: quiere vídeo y quiere que funcione. Elegir está disponible, pero no
#: se le exige a nadie para empezar.
#:
#: "sage" entra por defecto a propósito. Es un 2-4% más rápido que la
#: atención incluida, y dejarlo escondido en un menú significa que casi
#: nadie lo encuentra y todos renderizan más lento para siempre. Lo que
#: no puede pasar es que su ausencia rompa la instalación: por eso sus
#: pasos se marcan opcionales y, si no hay rueda para el equipo, se sigue
#: con la atención que ya trae ComfyUI.
PERFILES_POR_DEFECTO = ["h3", "wan", "ltx", "sage"]

#: Herramientas cuyo fallo no es un error: se intentan, y si no se puede,
#: hay un camino alternativo que funciona igual.
OPCIONALES = {"triton", "sageattention"}


def main():
    _consola_utf8()
    destino = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    py = os.path.join(destino, "python_embeded", "python.exe")
    if not os.path.isfile(py):
        py = sys.executable

    inf = deteccion.informe(python_exe=py, ruta_destino=destino)
    mostrar_equipo(inf)

    cuda = inf["cuda_recomendada"]
    perfiles = list(PERFILES_POR_DEFECTO)

    if not cuda and not inf["cuda_disponibles"]:
        print(f"\n   {R}{inf['cuda_motivo']}{X}")
        return 1

    # El camino corto: se enseña lo que se va a hacer y se pulsa Enter.
    # Quien quiera decidir, decide; a quien solo quiera instalar no se le
    # pide nada.
    titulo("Listo para instalar")
    print(f"   CUDA       {cuda}")
    print(f"   {G}{inf['cuda_motivo']}{X}")
    # Los perfiles eligen ACELERADORES, no modelos. Decir "perfiles:
    # MiniMax H3" hace pensar que se va a bajar el modelo, y son decenas
    # de gigas de diferencia entre lo que se entiende y lo que pasa.
    # Los modelos y los aceleradores se enseñan por separado: mezclarlos en
    # una lista hace pensar que SageAttention es un modelo que se descarga.
    modelos = [p for p in perfiles if catalogo.PERFILES[p]["herramientas"] == []]
    extras = [p for p in perfiles if catalogo.PERFILES[p]["herramientas"]]
    nombres = ", ".join(catalogo.PERFILES[p]["nombre"].split("  ·")[0] for p in modelos)
    print(f"\n   Preparado para: {nombres}")
    print(f"   Atención:       Comfy Kitchen {G}(incluida en ComfyUI){X}")
    if extras:
        nombres_extra = ", ".join(catalogo.PERFILES[p]["nombre"] for p in extras)
        print(f"   Se intentará:   {nombres_extra} {G}(un 2-4% más rápido;")
        print(f"                   si no hay versión para tu equipo, se omite){X}")
    print(f"\n   {A}NO se descarga ningún modelo.{X}")
    print(f"   {G}Esto instala ComfyUI y tus nodos, nada más. Los modelos los")
    print(f"   eliges y descargas tú después, cuando quieras, desde el nodo")
    print(f"   'Cine con IA · Modelos' dentro de ComfyUI.{X}\n")

    if preguntar("¿Empezamos?",
                 [("Sí, instalar con esto", "Lo habitual: pulsa Enter"),
                  ("Prefiero elegir yo", "Cambiar la rama de CUDA y anadir aceleradores")], 1) == 2:
        cuda = elegir_cuda(inf)
        if not cuda:
            return 1
        vram = inf["driver"]["vram_gb"] if inf["driver"] else None
        elegidos = elegir_perfiles(vram)
        if elegidos:
            perfiles = elegidos

    torch_rama = (inf["torch"] or {}).get("rama") or "2.8"
    py_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"

    herramientas = catalogo.herramientas_de(perfiles)

    # El camino normal no instala ningun acelerador: la atencion que traen
    # los perfiles de video ya viene dentro de ComfyUI. Enseñar una lista
    # vacia y pedir que la confirme seria pedirle que apruebe la nada.
    if herramientas:
        print(f"\n   {G}Buscando versiones compatibles...{X}")
        pasos = catalogo.plan(herramientas, torch_rama, cuda, py_tag)
        mostrar_plan(pasos)
        # Decir que no a un acelerador opcional no puede cancelar la
        # instalacion entera: los nodos y el enlace de modelos siguen
        # teniendo sentido sin el.
        if preguntar("¿Instalo esto?",
                     [("Sí", None), ("No, seguir sin ello", None)], 1) != 1:
            hechos, fallidos, omitidos = [], [], []
            print(f"\n   {G}De acuerdo, se sigue sin los aceleradores.{X}")
        else:
            hechos, fallidos, omitidos = ejecutar(pasos, py)
            verificar(hechos, py)
        if omitidos:
            titulo("Se siguió sin esto")
            for nombre, motivo in omitidos:
                print(f"   {nombre}: {G}{motivo}{X}")
            print(f"\n   {G}No pasa nada: son mejoras opcionales. ComfyUI va a")
            print(f"   usar su propia atención, que viene incluida.{X}")
        if fallidos:
            titulo("No se instaló")
            for nombre, motivo in fallidos:
                print(f"   {R}{nombre}{X}: {motivo}")
        # El lanzador arranca con lo que de verdad quedo instalado, no con
        # lo que se intento. Si SageAttention entro, se usa; si no, Kitchen.
        sage_ok = any(p["clave"] == "sageattention" for p in hechos)
        flag = "--use-sage-attention" if sage_ok else catalogo.FLAG_ATENCION
    else:
        print(f"\n   {G}No hace falta instalar ningún acelerador: la atención")
        print(f"   de Comfy Kitchen ya viene con ComfyUI.{X}")
        flag = catalogo.FLAG_ATENCION

    instalar_nodos(destino)
    ofrecer_enlace_modelos(destino)

    aviso_rutas = rutas_largas.aviso()
    if aviso_rutas:
        titulo("Un apunte sobre Windows")
        print(f"   {aviso_rutas}")

    titulo("Listo")
    nombre_atencion = ("SageAttention" if flag == "--use-sage-attention"
                       else "Comfy Kitchen")
    print(f"   Atención en uso: {A}{nombre_atencion}{X}")
    print(f"   Arranca ComfyUI y busca la categoría 'Cine con IA'.")
    print(f"   {G}Los modelos se descargan desde el nodo 'Modelos', cuando quieras.{X}")
    print(f"\n   {G}Tutoriales: {CANAL}{X}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
