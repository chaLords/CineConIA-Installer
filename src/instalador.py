"""Adaptive orchestrator: detect, propose, install and verify."""
from __future__ import annotations
import os, subprocess, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import catalogo, deteccion, entorno_torch, i18n, lanzadores, modelos_enlace, pasos, preflight, rutas_largas

# Nodos opcionales. "carpetas": nombres con que puede estar ya instalado;
# el primero es el que se usa al clonar.
NODOS={
    # Manager clasico como nodo: boton "Manager" en la barra, el de casi todos los
    # tutoriales. Su documentacion exige la carpeta custom_nodes/comfyui-manager.
    "manager":{"repo":"https://github.com/Comfy-Org/ComfyUI-Manager.git",
               "carpetas":["comfyui-manager","ComfyUI-Manager"],
               "pregunta":"installer.install_manager","detalle":"installer.manager_desc"},
    "cineconia":{"repo":"https://github.com/chaLords/ComfyUI-Cine-con-IA.git",
                 "carpetas":["ComfyUI-Cine-con-IA","ComfyUI-CineConIA","cine-con-ia"],
                 "pregunta":"installer.install_nodes","detalle":None},
    # Monitor de CPU, RAM, GPU, VRAM y temperatura en la barra superior.
    "monitor":{"repo":"https://github.com/crystian/ComfyUI-Crystools.git",
               "carpetas":["ComfyUI-Crystools","comfyui-crystools"],
               "pregunta":"installer.install_monitor","detalle":"installer.monitor_desc",
               # Su requirements pide "pynvml", hoy un envoltorio que solo avisa de que esta
               # obsoleto en cada arranque; el modulo real lo trae nvidia-ml-py.
               "sobrante":"pynvml"},
    # Grupo "video": lo que usan los workflows de MiniMax H3 y LTX. Una sola pregunta.
    "kjnodes":{"repo":"https://github.com/kijai/ComfyUI-KJNodes.git",
               "carpetas":["comfyui-kjnodes","ComfyUI-KJNodes"],"grupo":"video"},
    "vhs":{"repo":"https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git",
           "carpetas":["comfyui-videohelpersuite","ComfyUI-VideoHelperSuite"],"grupo":"video"},
    # Modelos GGUF: la forma de ahorrar VRAM en video (Nunchaku solo cubre imagen).
    "gguf":{"repo":"https://github.com/city96/ComfyUI-GGUF.git",
            "carpetas":["ComfyUI-GGUF","comfyui-gguf"],"grupo":"video"},
    "selflift":{"repo":"https://github.com/facok/comfyui-SelfLift.git",
                "carpetas":["comfyui-SelfLift","comfyui-selflift"],"grupo":"video"},
    # Escalador latente 3D de H3: sin el, "Escalar y refinar" de Cine con IA no
    # puede subir la resolucion del segundo pase.
    "h3upscaler":{"repo":"https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler.git",
                  "carpetas":["Comfyui_Minimax_h3_latent_Upscaler","comfyui_minimax_h3_latent_upscaler"],
                  "grupo":"video"},
    # Nodos de Nunchaku: sin ellos la wheel no aporta nada. Van con el perfil Nunchaku.
    "nunchaku":{"repo":"https://github.com/nunchux-ai/ComfyUI-nunchaku.git",
                "carpetas":["ComfyUI-nunchaku","comfyui-nunchaku"]},
}
A,G,R,X="\033[38;5;179m","\033[38;5;245m","\033[38;5;203m","\033[0m"
t=i18n.t
SI_NO=lambda:[(t("common.yes"),None),(t("common.no"),None)]

def titulo(texto):
    print(f"\n{A}{'='*62}\n  {texto}\n{'='*62}{X}")

def preguntar(texto,opciones,defecto=1):
    for i,(etiqueta,detalle) in enumerate(opciones,1):
        recomendado=f" {A}({t('common.recommended')}){X}" if i==defecto else ""
        print(f"   {i}) {etiqueta}{recomendado}")
        if detalle:
            print(f"      {G}{detalle}{X}")
    while True:
        r=input(f"\n   {texto} [{defecto}]: ").strip()
        if not r:
            return defecto
        if r.isdigit() and 1<=int(r)<=len(opciones):
            return int(r)

def marcar(texto,opciones):
    for i,(etiqueta,detalle) in enumerate(opciones,1):
        print(f"   {i}) {etiqueta}")
        if detalle:
            print(f"      {G}{detalle}{X}")
    r=input("\n   "+t("installer.select_extras_hint",text=texto)).strip()
    if not r:
        return []
    return [int(x) for x in r.replace(","," ").split()
            if x.isdigit() and 1<=int(x)<=len(opciones)]

def mostrar_equipo(inf):
    print(f"   GPU          {inf['gpu']}")
    if inf.get("vram_gb") is not None:
        print(f"   VRAM         {inf['vram_gb']} GB")
    print(f"   {t('installer.manufacturer'):<12} {inf['fabricante']}")
    print(f"   Backend      {inf['backend']}")
    print(f"   PyTorch      {inf['torch'].get('torch') or t('common.unavailable')}")
    print(f"   Python       {inf['python']}")
    print(f"   {t('installer.free_space'):<12} {t('installer.free_space_value',value=inf['espacio_gb'])}")

def preflight_usuario(destino):
    sano,faltan=preflight.salud_comfyui(destino)
    if not sano:
        titulo(t("installer.incomplete"))
        print(f"   {R}{', '.join(faltan)}{X}")
        return False
    if preflight.vcredist_instalado() is False:
        titulo("Microsoft Visual C++")
        print("   "+t("installer.vcredist_missing"))
        if preflight.winget_exe() and preguntar(t("installer.install_vcredist"),SI_NO(),1)==1:
            ok,msg=preflight.instalar_vcredist()
            print(f"   {A if ok else R}{msg}{X}")
        else:
            print("   https://aka.ms/vc14/vc_redist.x64.exe")
    aviso=rutas_largas.aviso()
    if aviso:
        titulo(t("installer.long_paths"))
        print("   "+aviso)
    if not preflight.git_exe():
        titulo("Git")
        print("   "+t("installer.git_required"))
        opciones=[(t("common.yes"),None),(t("common.no"),t("installer.nodes_will_be_skipped"))]
        if preflight.winget_exe() and preguntar(t("installer.install_git"),opciones,1)==1:
            ok,msg=preflight.instalar_git()
            print(f"   {A if ok else R}{msg}{X}")
    return True

def gpu_utilizable(inf):
    """Avisa si PyTorch no puede usar la GPU. Devuelve False si el usuario sale."""
    if not inf.get("gpu_inutilizable"):
        return True
    titulo(t("installer.gpu_unusable_title"))
    print(f"   {R}{t('installer.gpu_unusable')}{X}")
    if inf.get("gpu_error"):
        print(f"   {G}{inf['gpu_error']}{X}")
    if inf["fabricante"]=="nvidia":
        print("   https://www.nvidia.com/drivers")
    elif inf["fabricante"]=="amd":
        print("   https://www.amd.com/support")
    return preguntar(t("installer.continue_anyway"),[(t("common.no"),None),(t("common.yes"),None)],1)==2

def elegir_perfiles(vram):
    claves=list(catalogo.PERFILES)
    opts=[]
    for clave in claves:
        p=catalogo.PERFILES[clave]
        aviso=""
        if vram and p["vram_min"]>vram:
            aviso=t("installer.vram_note",needed=p["vram_min"],have=vram)
        opts.append((t(f"profile.{clave}.name")+aviso,t(f"profile.{clave}.detail")))
    return [claves[i-1] for i in marcar(t("installer.select_extras"),opts)]

def mostrar_plan(plan):
    print(f"\n   {A}{t('installer.accelerator_plan')}{X}")
    n=0
    for p in plan:
        print(f"\n   {A}{p['nombre']}{X}")
        if p["url"]:
            print("      wheel: "+os.path.basename(p["url"]))
            n+=1
        elif p["spec"]:
            print("      pip:   "+p["spec"])
            n+=1
        if p["aviso"]:
            print(f"      {R}{t('installer.omitted')}: {p['aviso']}{X}")
        print(f"      {G}{p['licencia']}{X}")
    return n

def pip_instalar(py,args,nombre):
    """pip con indicador de una linea; el detalle completo va a instalacion.log."""
    ok,cola=pasos.correr(
        [py,"-s","-m","pip","install","--no-cache-dir","--timeout","600","--retries","5"]+args,
        f"pip: {nombre}")
    if ok:
        print(f"   {pasos.V}{pasos.MARCAS['ok'][0]}{X} {nombre}")
    else:
        print(f"   {R}{pasos.MARCAS['fallo'][0]} {nombre}{X}")
        for linea in cola[-3:]:
            print(f"      {G}{linea[:110]}{X}")
    return ok

def ejecutar(pasos,py):
    ok,omitidos,fallidos=[],[],[]
    for p in pasos:
        if not p["url"] and not p["spec"]:
            omitidos.append((p["nombre"],p["aviso"] or t("installer.no_compatible_package")))
            continue
        destino=[p["url"]] if p["url"] else [p["spec"]]
        if pip_instalar(py,destino,p["nombre"]):
            ok.append(p)
        else:
            fallidos.append((p["nombre"],t("installer.pip_error")))
    return ok,omitidos,fallidos

def _probar(py,clave):
    """(ok, detalle). Usa la prueba funcional si la herramienta la define."""
    h=catalogo.HERRAMIENTAS[clave]
    mod=h.get("modulo")
    codigo=h.get("prueba") or f"import {mod}; print(getattr({mod},'__version__','OK'))"
    try:
        r=subprocess.run([py,"-s","-c",codigo],capture_output=True,text=True,timeout=180)
    except (OSError,subprocess.SubprocessError) as e:
        return False,str(e)
    if r.returncode==0:
        return True,(r.stdout.strip().splitlines() or ["OK"])[-1]
    return False,(r.stderr.strip().splitlines() or ["error"])[-1][:100]

def _presente(py,modulo):
    try:
        return subprocess.run(
            [py,"-s","-c",f"import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('{modulo}') else 1)"],
            capture_output=True,timeout=45
        ).returncode==0
    except (OSError,subprocess.SubprocessError):
        return False

def verificar(claves,py,solo_presentes=False):
    """Prueba cada herramienta. Con solo_presentes, ignora en silencio lo no instalado."""
    verificados,fallos=set(),[]
    for clave in claves:
        h=catalogo.HERRAMIENTAS[clave]
        if not h.get("modulo"):
            verificados.add(clave)
            continue
        if solo_presentes and not _presente(py,h["modulo"]):
            continue
        ok,detalle=_probar(py,clave)
        if ok:
            verificados.add(clave)
            print(f"   {A}{t('common.ok')}{X}   {h['nombre']} {detalle}")
        else:
            fallos.append((h["nombre"],detalle))
            print(f"   {R}{t('installer.import_failed')}{X} {h['nombre']}: {detalle[:80]}")
    return verificados,fallos

def conflictos_pip(py):
    """Lineas de 'pip check': paquetes con dependencias incompatibles."""
    try:
        r=subprocess.run([py,"-s","-m","pip","check"],capture_output=True,text=True,timeout=120)
    except (OSError,subprocess.SubprocessError):
        return []
    return [] if r.returncode==0 else [l for l in r.stdout.splitlines() if l.strip()]

def ofrecer_manager(destino,py,torch_base=None):
    """Devuelve "clasico", "integrado" o None.

    Se prefiere el Manager clasico como nodo. El integrado de ComfyUI
    (--enable-manager) tiene otra interfaz y, activado, desactiva el clasico:
    solo se usa si no hay Git para clonar el clasico.
    """
    if preflight.git_exe():
        return "clasico" if instalar_nodo(destino,py,"manager",torch_base) else None
    if not lanzadores.flag_soportado(destino,"--enable-manager"):
        return None
    if not lanzadores.manager_integrado(destino):
        req=os.path.join(destino,"ComfyUI","manager_requirements.txt")
        print("\n   "+t("installer.manager_desc"))
        if not os.path.isfile(req) or preguntar(t("installer.install_manager"),SI_NO(),1)!=1:
            return None
        pip_instalar(py,["-r",req],"ComfyUI-Manager")
    return "integrado" if lanzadores.manager_integrado(destino) else None

def instalar_requisitos(py,req,nombre):
    """pip -r; si falla, requisito por requisito. Devuelve los que no se instalaron.

    Un solo paquete que no compila en Windows (insightface sin Visual C++, por
    ejemplo) hace fallar el -r entero y deja al nodo sin nada.
    """
    if pip_instalar(py,["-r",req],nombre):
        return []
    fallidos=[]
    with open(req,encoding="utf-8",errors="replace") as f:
        for linea in f:
            linea=linea.split("#",1)[0].strip()
            if linea and not linea.startswith("-") and not pip_instalar(py,[linea],f"{nombre}: {linea}"):
                fallidos.append(linea)
    return fallidos

def nodo_instalado(destino,clave):
    custom=os.path.join(destino,"ComfyUI","custom_nodes")
    return any(os.path.isdir(os.path.join(custom,n)) for n in NODOS[clave]["carpetas"])

def clonar_nodo(destino,py,clave,torch_base=None):
    """Clona el nodo e instala sus requisitos, vigilando que no toquen PyTorch."""
    nodo=NODOS[clave]
    git=preflight.git_exe()
    if not git:
        return False
    custom=os.path.join(destino,"ComfyUI","custom_nodes")
    os.makedirs(custom,exist_ok=True)
    ruta=os.path.join(custom,nodo["carpetas"][0])
    ok,cola=pasos.correr([git,"clone","--depth","1",nodo["repo"],ruta],f"git clone {nodo['carpetas'][0]}")
    if not ok:
        print(f"   {R}{pasos.MARCAS['fallo'][0]} {nodo['carpetas'][0]}{X}")
        for linea in cola[-3:]:
            print(f"      {G}{linea[:110]}{X}")
        return False
    print(f"   {pasos.V}{pasos.MARCAS['ok'][0]}{X} {nodo['carpetas'][0]}")
    req=os.path.join(ruta,"requirements.txt")
    if os.path.isfile(req):
        for paquete in instalar_requisitos(py,req,nodo["carpetas"][0]):
            print(f"   {R}{t('installer.req_failed',package=paquete,node=nodo['carpetas'][0])}{X}")
    if nodo.get("sobrante"):
        pasos.correr([py,"-s","-m","pip","uninstall","-y",nodo["sobrante"]],f"pip uninstall {nodo['sobrante']}")
    proteger_torch(py,torch_base)
    return True

def instalar_nodo(destino,py,clave,torch_base=None):
    nodo=NODOS[clave]
    if nodo_instalado(destino,clave):
        return True
    if not preflight.git_exe():
        return False
    if nodo.get("detalle"):
        print("\n   "+t(nodo["detalle"]))
    if preguntar(t(nodo["pregunta"]),SI_NO(),1)!=1:
        return False
    return clonar_nodo(destino,py,clave,torch_base)

def instalar_grupo(destino,py,grupo,torch_base=None):
    """Una sola pregunta para un grupo de nodos. Devuelve los que quedaron instalados."""
    claves=[c for c,n in NODOS.items() if n.get("grupo")==grupo]
    faltan=[c for c in claves if not nodo_instalado(destino,c)]
    if faltan and preflight.git_exe():
        print("\n   "+t(f"installer.{grupo}_nodes_desc"))
        if preguntar(t(f"installer.install_{grupo}_nodes"),SI_NO(),1)==1:
            for clave in faltan:
                clonar_nodo(destino,py,clave,torch_base)
    return [c for c in claves if nodo_instalado(destino,c)]

def proteger_torch(py,antes):
    """Si algo reinstalo PyTorch por su cuenta, se devuelve a la version anterior."""
    cambio,restaurado=entorno_torch.vigilar(py,antes,pip_instalar)
    if cambio:
        print(f"   {A if restaurado else R}{t('installer.torch_restored' if restaurado else 'installer.torch_restore_failed')}{X}")

def preparar_nunchaku(destino,py,inf):
    """Nunchaku solo publica wheels hasta cierta rama de PyTorch. Si la instalada
    es mas nueva, ofrece cambiar a la ultima compatible con la misma CUDA.
    Devuelve True si PyTorch cambio (hay que volver a detectar el entorno)."""
    if inf["fabricante"]!="nvidia" or not inf.get("cuda"):
        return False
    py_tag=f"cp{sys.version_info.major}{sys.version_info.minor}"
    ramas=catalogo.ramas_con_rueda(catalogo.HERRAMIENTAS["nunchaku"]["repo"],inf["cuda"],py_tag)
    actual=catalogo._version(inf["torch_rama"])
    if not ramas or actual in ramas:
        return False
    compatibles=[r for r in ramas if r<actual]
    if not compatibles:
        return False
    objetivo=compatibles[-1]
    titulo("Nunchaku")
    print("   "+t("installer.nunchaku_needs",need=f"{objetivo[0]}.{objetivo[1]}",have=inf["torch_rama"]))
    if preguntar(t("installer.nunchaku_switch"),SI_NO(),1)!=1:
        return False
    ruta=entorno_torch.guardar_estado(destino,py)
    if ruta:
        print(f"   {G}{t('installer.state_saved',path=ruta)}{X}")
    ok,detalle=entorno_torch.cambiar_rama(py,objetivo,inf["torch"].get("torch"),pip_instalar)
    print(f"   {A if ok else R}{t('installer.torch_switched' if ok else 'installer.torch_switch_failed',version=detalle)}{X}")
    return ok

def ofrecer_enlace_modelos(destino):
    """Busca modelos de instalaciones anteriores y solo pregunta si encuentra algo."""
    destino_comfy=os.path.join(destino,"ComfyUI")
    real=lambda p:os.path.normcase(os.path.realpath(p))
    propia=real(os.path.join(destino_comfy,"models"))
    print(f"   {G}{t('installer.searching_models')}{X}")
    encontradas=[p for p in modelos_enlace.detectar_instalaciones() if real(p)!=propia]
    # La biblioteca central que dejo el migrador va primero: es la que deben
    # compartir todas las instalaciones futuras.
    central=lambda p:os.path.isdir(os.path.join(p,"_cineconia_migracion"))
    con_tamano=[(p,modelos_enlace.tamano_bytes(p)/1e9) for p in encontradas]
    con_tamano=sorted([x for x in con_tamano if x[1]>0],key=lambda x:(not central(x[0]),-x[1]))[:5]
    if not con_tamano:
        print(f"   {G}{t('installer.no_models_found')}{X}")
        return None
    etiqueta=lambda p,gb:f"{gb:.1f} GB - {p}"+(f" {A}[{t('installer.central_library')}]{X}" if central(p) else "")
    print("   "+t("installer.models_found"))
    for p,gb in con_tamano:
        print("   - "+etiqueta(p,gb))
    accion=preguntar(t("installer.models_what"),[
        (t("installer.models_link"),t("installer.models_link_desc")),
        (t("installer.models_migrate"),t("installer.models_migrate_desc")),
        (t("installer.models_nothing"),t("installer.search_models_no")),
    ],1)
    if accion==3:
        return None
    if accion==2:
        # El mismo migrador del BAT, con simulacion y confirmacion MIGRAR.
        # Al terminar tambien enlaza este ComfyUI a la biblioteca nueva.
        import migrar_modelos
        migrar_modelos.main(encontrados=[p for p,_ in con_tamano],instalaciones_extra=[destino_comfy])
        return "migrated"
    models=con_tamano[0][0]
    if len(con_tamano)>1:
        eleccion=preguntar(t("installer.which_models"),[(etiqueta(p,gb),None) for p,gb in con_tamano],1)
        models=con_tamano[eleccion-1][0]
    try:
        _,backup=modelos_enlace.actualizar_yaml(destino_comfy,models,modelos_enlace.mapa_categorias(models))
    except OSError as e:
        print(f"   {R}{t('installer.no_changes',error=e)}{X}")
        return None
    print(f"   {A}{t('installer.models_linked')}{X}")
    if backup:
        print(f"   {G}{backup}{X}")
    if not central(models):
        print(f"   {G}{t('installer.migrator_hint')}{X}")
    return "linked"

# Pasos que muestra este script; los del .bat (equipo, descarga, extraccion)
# se suman delante. Ver pasos.py.
TITULOS=["installer.step_environment","installer.step_accelerators","installer.step_verify",
         "installer.step_manager","installer.step_nodes","installer.step_monitor",
         "installer.step_video","installer.step_models","installer.step_launchers"]

def main():
    os.system("")  # activa los colores ANSI en la consola clasica de Windows 10
    destino=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.getcwd())
    fabricante=sys.argv[2] if len(sys.argv)>2 else None
    variante=sys.argv[3] if len(sys.argv)>3 else None
    py=os.path.join(destino,"python_embeded","python.exe")
    pasos.usar_log(destino)
    P=pasos.Pasos([t(k) for k in TITULOS])
    if not preflight_usuario(destino):
        return 1

    P.empezar(t("installer.step_environment"))
    inf=deteccion.informe(py,destino,fabricante,variante)
    mostrar_equipo(inf)
    if not inf["torch"].get("torch"):
        print(f"\n   {R}{t('installer.pytorch_broken')}{X}")
        P.cerrar("fallo","PyTorch")
        P.resumen()
        return 1
    if not gpu_utilizable(inf):
        P.cerrar("fallo",inf["gpu"])
        P.resumen()
        return 1
    P.cerrar("ok",f"{inf['gpu']} · {inf['backend']}")

    P.empezar(t("installer.step_accelerators"))
    perfiles=["sage"] if inf["fabricante"]=="nvidia" and not inf.get("gpu_inutilizable") else []
    opciones=[
        (t("installer.auto"),t("installer.auto_desc")),
        (t("installer.advanced"),t("installer.advanced_desc")),
    ]
    if preguntar(t("installer.continue"),opciones,1)==2:
        perfiles=elegir_perfiles(inf.get("vram_gb"))
    herramientas=catalogo.herramientas_de(perfiles)
    if "nunchaku" in herramientas and preparar_nunchaku(destino,py,inf):
        inf=deteccion.informe(py,destino,fabricante,variante)
        mostrar_equipo(inf)
    # Version de PyTorch "buena": ningun extra ni nodo puede cambiarla sin permiso.
    torch_base=entorno_torch.versiones(py)
    cierre=("omitido",t("installer.not_applicable") if inf["fabricante"]!="nvidia" else t("installer.skipped"))
    if herramientas:
        plan=catalogo.plan(herramientas,inf,f"cp{sys.version_info.major}{sys.version_info.minor}")
        if mostrar_plan(plan) and preguntar(t("installer.install_compatible"),SI_NO(),1)==1:
            instalados,omitidos,fallidos=ejecutar(plan,py)
            proteger_torch(py,torch_base)
            for nombre,motivo in omitidos+fallidos:
                print(f"   {R}{nombre}{X}: {motivo}")
            if any(p["clave"]=="nunchaku" for p in instalados) and not nodo_instalado(destino,"nunchaku"):
                clonar_nodo(destino,py,"nunchaku",torch_base)
            nombres=", ".join(p["nombre"] for p in instalados) or t("common.none")
            cierre=("fallo" if fallidos else ("ok" if instalados else "omitido"),nombres)
    P.cerrar(*cierre)

    # Se verifica todo lo que haya, instalado ahora o en una ejecucion anterior:
    # asi repetir el instalador nunca degrada el acceso directo.
    P.empezar(t("installer.step_verify"))
    if _presente(py,"triton"):
        # Este script corre con el python_embeded del portable: su version es la nuestra.
        ok,msg=catalogo.cabeceras_python(os.path.dirname(py),sys.version_info)
        if msg:
            print(f"   {A if ok else R}{msg}{X}")
    verificados,fallos=verificar(list(catalogo.HERRAMIENTAS),py,solo_presentes=True)
    probados=[catalogo.HERRAMIENTAS[c]["nombre"] for c in catalogo.HERRAMIENTAS
              if c in verificados and catalogo.HERRAMIENTAS[c].get("modulo")]
    P.cerrar("fallo" if fallos else ("ok" if probados else "omitido"),", ".join(probados) or t("common.none"))

    P.empezar(t("installer.step_manager"))
    manager=ofrecer_manager(destino,py,torch_base)
    P.cerrar("ok" if manager else "omitido",t("installer.manager_"+manager) if manager else t("common.not_active"))

    P.empezar(t("installer.step_nodes"))
    nodos_ok=instalar_nodo(destino,py,"cineconia",torch_base)
    P.cerrar("ok" if nodos_ok else "omitido",t("installer.installed") if nodos_ok else t("common.not_installed"))

    P.empezar(t("installer.step_monitor"))
    monitor_ok=instalar_nodo(destino,py,"monitor",torch_base)
    P.cerrar("ok" if monitor_ok else "omitido",t("installer.installed") if monitor_ok else t("common.not_installed"))

    P.empezar(t("installer.step_video"))
    video=instalar_grupo(destino,py,"video",torch_base)
    del_grupo=[c for c,n in NODOS.items() if n.get("grupo")=="video"]
    estado="ok" if len(video)==len(del_grupo) else ("omitido" if not video else "fallo")
    P.cerrar(estado,t("installer.n_of_m",n=len(video),m=len(del_grupo)))
    problemas=conflictos_pip(py)

    P.empezar(t("installer.step_models"))
    modelos=ofrecer_enlace_modelos(destino)
    P.cerrar("ok" if modelos else "omitido",t(f"installer.step_models_{modelos or 'none'}"))

    P.empezar(t("installer.step_launchers"))
    creados,preferido=lanzadores.crear_lanzadores(destino,inf,verificados,manager)
    for _,ruta in creados.items():
        print(f"   {pasos.V}{pasos.MARCAS['ok'][0]}{X} {os.path.basename(ruta)}")
    ok,detalle=lanzadores.crear_acceso_escritorio(destino,preferido)
    P.cerrar("ok" if ok else "fallo",t("installer.desktop_shortcut"))

    # Datos del equipo que quedan de referencia, encima del resumen de pasos.
    print(f"\n   {G}Backend: {inf['backend']}  ·  PyTorch: {inf['torch'].get('torch')}  ·  "
          f"{t('installer.main_launcher')}: {os.path.basename(preferido)}{X}")
    if problemas:
        print(f"   {R}{t('installer.pip_conflicts',count=len(problemas))}{X}")
        for linea in problemas[:8]:
            print(f"      {G}{linea}{X}")
    P.resumen()
    print(f"\n   {A}{t('installer.ready')}{X}")
    return 0

if __name__=="__main__":
    sys.exit(main())
