"""Adaptive orchestrator: detect, propose, install and verify."""
from __future__ import annotations
import os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import ajustes_interfaz, catalogo, deteccion, entorno_torch, i18n, lanzadores, modelos_enlace, pasos, preflight, rutas_largas, verificacion

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
    # Grupo "interfaz": ayudas de pantalla, sin dependencias de Python.
    # rgthree-comfy dibuja la barra de progreso verde de arriba (cola, porcentaje
    # y nodo que corre) y trae nodos muy usados (Fast Groups Bypasser, Power Lora
    # Loader...). Custom-Scripts agrega Image Feed y el autocompletado.
    "rgthree":{"repo":"https://github.com/rgthree/rgthree-comfy.git",
               "carpetas":["rgthree-comfy"],"grupo":"interfaz"},
    "customscripts":{"repo":"https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git",
                     "carpetas":["comfyui-custom-scripts","ComfyUI-Custom-Scripts"],"grupo":"interfaz"},
    # Grupo "comunidad": lo que piden muchos workflows compartidos. Traen
    # dependencias pesadas, por eso la respuesta por defecto es No. ControlNet
    # aux va al final: su onnxruntime-gpu queda encima si otro trajo el de CPU.
    "essentials":{"repo":"https://github.com/cubiq/ComfyUI_essentials.git",
                  "carpetas":["comfyui_essentials","ComfyUI_essentials"],"grupo":"comunidad"},
    "comfyroll":{"repo":"https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes.git",
                 "carpetas":["ComfyUI_Comfyroll_CustomNodes","comfyroll"],"grupo":"comunidad"},
    "was":{"repo":"https://github.com/ltdrdata/was-node-suite-comfyui.git",
           "carpetas":["was-ns","was-node-suite-comfyui"],"grupo":"comunidad"},
    "controlnet_aux":{"repo":"https://github.com/Fannovel16/comfyui_controlnet_aux.git",
                      "carpetas":["comfyui_controlnet_aux"],"grupo":"comunidad"},
    # Nodos de Nunchaku: sin ellos la wheel no aporta nada. Van con el perfil Nunchaku.
    "nunchaku":{"repo":"https://github.com/nunchux-ai/ComfyUI-nunchaku.git",
                "carpetas":["ComfyUI-nunchaku","comfyui-nunchaku"]},
}
# Respuesta por defecto de cada grupo (1 = Si, 2 = No).
DEFECTO_GRUPO={"video":1,"interfaz":1,"comunidad":2}
A,G,R,X="\033[38;5;179m","\033[38;5;245m","\033[38;5;203m","\033[0m"
t=i18n.t
SI_NO=lambda:[(t("common.yes"),None),(t("common.no"),None)]
ESTADOS_NODOS={}
RESTRICCIONES_TORCH=None

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
    restricciones=["--constraint",RESTRICCIONES_TORCH] if RESTRICCIONES_TORCH else []
    ok,cola=pasos.correr(
        [py,"-s","-m","pip","install","--no-cache-dir","--timeout","600","--retries","5"]+restricciones+args,
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

# Avisos de "pip check" que trae el propio portable oficial y no afectan a
# ComfyUI: comfyui-workflow-templates declara sus paquetes de imagenes de
# ejemplo, que el portable no incluye. Salian en rojo en toda instalacion
# nueva y parecia que algo habia fallado.
CONFLICTOS_CONOCIDOS=("comfyui-workflow-templates-media-",)

def conflictos_pip(py):
    """Lineas de 'pip check' que importan. Las conocidas e inofensivas van solo al registro."""
    try:
        r=subprocess.run([py,"-s","-m","pip","check"],capture_output=True,text=True,timeout=120)
    except (OSError,subprocess.SubprocessError) as e:
        return [t("installer.pip_check_failed",error=str(e))]
    if r.returncode==0:
        return []
    lineas=[l for l in r.stdout.splitlines() if l.strip()]
    pasos.registrar("pip check",r.stdout+"\n"+r.stderr)
    if not lineas:
        return [t("installer.pip_check_failed",error=r.stderr.strip() or str(r.returncode))]
    return [l for l in lineas if not any(c in l for c in CONFLICTOS_CONOCIDOS)]

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
        if not pip_instalar(py,["-r",req],"ComfyUI-Manager"):
            ESTADOS_NODOS["manager"]="fallo"
            return None
        proteger_torch(py,torch_base)
    return "integrado" if lanzadores.manager_integrado(destino) else None

def instalar_requisitos(py,req,nombre):
    """pip -r; si falla, requisito por requisito. Devuelve los que no se instalaron.

    Un solo paquete que no compila en Windows (insightface sin Visual C++, por
    ejemplo) hace fallar el -r entero y deja al nodo sin nada.
    """
    if pip_instalar(py,["-r",req],f"{nombre} · requirements.txt"):
        return []
    fallidos=[]
    with open(req,encoding="utf-8",errors="replace") as f:
        lineas=[re.split(r"\s+#",linea,maxsplit=1)[0].strip() for linea in f]
    lineas=[l for l in lineas if l and not l.startswith("#")]
    # No reinterpretar includes, constraints, URLs con fragmentos o continuaciones:
    # pip ya los proceso correctamente y el fallo original debe seguir visible.
    if not lineas or any(l.startswith("-") or l.endswith("\\") or l.startswith((".","/")) for l in lineas):
        return [os.path.basename(req)]
    for linea in lineas:
        if not pip_instalar(py,[linea],f"{nombre}: {linea}"):
            fallidos.append(linea)
    return fallidos

def ruta_nodo(destino,clave):
    custom=os.path.join(destino,"ComfyUI","custom_nodes")
    return next((os.path.join(custom,n) for n in NODOS[clave]["carpetas"]
                 if os.path.isdir(os.path.join(custom,n))),None)

def nodo_instalado(destino,clave):
    ruta=ruta_nodo(destino,clave)
    return bool(ruta and os.path.isfile(os.path.join(ruta,"__init__.py")))

def clonar_nodo(destino,py,clave,torch_base=None):
    try:
        return _preparar_nodo(destino,py,clave,torch_base)
    except OSError as e:
        ESTADOS_NODOS[clave]="fallo"
        pasos.registrar("nodo: "+clave,str(e))
        print(f"   {R}{pasos.MARCAS['fallo'][0]} {clave}: {e}{X}")
        return False

def _preparar_nodo(destino,py,clave,torch_base=None):
    """Clona el nodo e instala sus requisitos, vigilando que no toquen PyTorch."""
    nodo=NODOS[clave]
    ESTADOS_NODOS[clave]="fallo"
    custom=os.path.join(destino,"ComfyUI","custom_nodes")
    os.makedirs(custom,exist_ok=True)
    ruta=ruta_nodo(destino,clave) or os.path.join(custom,nodo["carpetas"][0])
    if not nodo_instalado(destino,clave):
        git=preflight.git_exe()
        if not git:
            return False
        # Una descarga incompleta nunca aparece como nodo instalado. Guardar la
        # carpeta anterior fuera de custom_nodes; no borrar archivos del usuario.
        trabajo=os.path.join(destino,"_cineconia","descargas-nodos")
        os.makedirs(trabajo,exist_ok=True)
        temporal=tempfile.mkdtemp(prefix=clave+"-",dir=trabajo)
        ok,cola=pasos.correr([git,"clone","--depth","1",nodo["repo"],temporal],f"git clone {nodo['carpetas'][0]}")
        if not ok or not os.path.isfile(os.path.join(temporal,"__init__.py")):
            print(f"   {R}{pasos.MARCAS['fallo'][0]} {nodo['carpetas'][0]}{X}")
            for linea in cola[-3:]:
                print(f"      {G}{linea[:110]}{X}")
            return False
        if os.path.exists(ruta):
            respaldo=temporal+"-anterior"
            os.rename(ruta,respaldo)
            print("   "+t("installer.node_backup",path=respaldo))
        os.rename(temporal,ruta)
    req=os.path.join(ruta,"requirements.txt")
    fallidos=[]
    if os.path.isfile(req):
        fallidos=instalar_requisitos(py,req,nodo["carpetas"][0])
        for paquete in fallidos:
            print(f"   {R}{t('installer.req_failed',package=paquete,node=nodo['carpetas'][0])}{X}")
    if nodo.get("sobrante"):
        # El sustituto debe existir antes de quitar el envoltorio obsoleto.
        if pip_instalar(py,["nvidia-ml-py"],"NVML"):
            pasos.correr([py,"-s","-m","pip","uninstall","-y",nodo["sobrante"]],f"pip uninstall {nodo['sobrante']}")
    proteger_torch(py,torch_base)
    ESTADOS_NODOS[clave]="fallo" if fallidos else "ok"
    return not fallidos

def instalar_nodo(destino,py,clave,torch_base=None):
    nodo=NODOS[clave]
    if ruta_nodo(destino,clave):
        return clonar_nodo(destino,py,clave,torch_base)
    ESTADOS_NODOS[clave]="omitido"
    if not preflight.git_exe():
        return False
    if nodo.get("detalle"):
        print("\n   "+t(nodo["detalle"]))
    if preguntar(t(nodo["pregunta"]),SI_NO(),1)!=1:
        return False
    return clonar_nodo(destino,py,clave,torch_base)

def instalar_grupo(destino,py,grupo,torch_base=None):
    """Una sola pregunta para un grupo de nodos.

    Devuelve (instalados, aceptado). aceptado es None si no hubo que preguntar
    (ya estaba todo o no hay Git)."""
    claves=[c for c,n in NODOS.items() if n.get("grupo")==grupo]
    existentes=[c for c in claves if ruta_nodo(destino,c)]
    for clave in existentes:
        clonar_nodo(destino,py,clave,torch_base)
    faltan=[c for c in claves if c not in existentes]
    aceptado=None
    if faltan and preflight.git_exe():
        print("\n   "+t(f"installer.{grupo}_nodes_desc"))
        aceptado=preguntar(t(f"installer.install_{grupo}_nodes"),SI_NO(),DEFECTO_GRUPO.get(grupo,1))==1
        if aceptado:
            for clave in faltan:
                clonar_nodo(destino,py,clave,torch_base)
    return [c for c in claves if ESTADOS_NODOS.get(c)=="ok"],aceptado

def paso_grupo(P,destino,py,grupo,torch_base=None):
    """Un paso por grupo: listo si esta todo, fallo solo si se pidio y algo no
    quedo, omitido si se dijo que no (aunque ya hubiera alguno de antes)."""
    instalados,aceptado=instalar_grupo(destino,py,grupo,torch_base)
    total=len([c for c,n in NODOS.items() if n.get("grupo")==grupo])
    fallo=any(ESTADOS_NODOS.get(c)=="fallo" for c,n in NODOS.items() if n.get("grupo")==grupo)
    estado="fallo" if fallo else ("ok" if len(instalados)==total else ("fallo" if aceptado else "omitido"))
    P.cerrar(estado,t("installer.n_of_m",n=len(instalados),m=total))
    return instalados

def git_en_path():
    """pip necesita git en el PATH para los requisitos "git+https://..." (WAS los
    usa). Si Git se acaba de instalar, esta consola todavia no lo ve."""
    git=preflight.git_exe()
    if git and not shutil.which("git"):
        os.environ["PATH"]=os.path.dirname(git)+os.pathsep+os.environ.get("PATH","")

def proteger_torch(py,antes):
    """Si algo reinstalo PyTorch por su cuenta, se devuelve a la version anterior."""
    cambio,restaurado=entorno_torch.vigilar(py,antes,pip_instalar)
    if cambio:
        print(f"   {A if restaurado else R}{t('installer.torch_restored' if restaurado else 'installer.torch_restore_failed')}{X}")
    if not restaurado:
        raise entorno_torch.EntornoNoRecuperado(t("installer.torch_restore_failed"))
    return True

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
    for ruta in modelos_enlace.bibliotecas_guardadas():
        if not os.path.isdir(ruta):
            print(f"   {A}{t('installer.library_offline',path=ruta)}{X}")
    encontradas=[p for p in modelos_enlace.detectar_instalaciones() if real(p)!=propia]
    # La biblioteca central que dejo el migrador va primero: es la que deben
    # compartir todas las instalaciones futuras.
    central=modelos_enlace.es_central
    con_tamano=[(p,modelos_enlace.tamano_bytes(p)/1e9) for p in encontradas]
    guardadas={real(p):i for i,p in enumerate(modelos_enlace.bibliotecas_guardadas())}
    con_tamano=sorted([x for x in con_tamano if x[1]>0 or central(x[0])],
        key=lambda x:(guardadas.get(real(x[0]),len(guardadas)+(0 if central(x[0]) else 1)),-x[1]))[:5]
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
        resultado=migrar_modelos.main(encontrados=[p for p,_ in con_tamano],instalaciones_extra=[destino_comfy])
        if resultado is None:
            return None
        if resultado:
            return "error"
        return "migrated"
    models=con_tamano[0][0]
    if len(con_tamano)>1:
        eleccion=preguntar(t("installer.which_models"),[(etiqueta(p,gb),None) for p,gb in con_tamano],1)
        models=con_tamano[eleccion-1][0]
    try:
        if central(models):
            modelos_enlace.registrar_biblioteca(models)
        _,backup=modelos_enlace.actualizar_yaml(destino_comfy,models,modelos_enlace.mapa_categorias(models))
    except OSError as e:
        print(f"   {R}{t('installer.no_changes',error=e)}{X}")
        return "error"
    print(f"   {A}{t('installer.models_linked')}{X}")
    if backup:
        print(f"   {G}{backup}{X}")
    if not central(models):
        print(f"   {G}{t('installer.migrator_hint')}{X}")
    return "linked"

def ajustar_interfaz(destino):
    """Cola de trabajos acoplada al panel lateral, sin el panel flotante de
    progreso. No pisa lo que el usuario ya haya elegido en ComfyUI."""
    estado,detalle=ajustes_interfaz.aplicar(destino)
    if estado=="ok":
        print(f"   {pasos.V}{pasos.MARCAS['ok'][0]}{X} {t('installer.ui_settings_applied')}")
        if detalle:
            print(f"      {G}{detalle}{X}")
    elif estado=="igual":
        print(f"   {G}{t('installer.ui_settings_kept')}{X}")
    else:
        print(f"   {A}{t('installer.ui_settings_failed',error=detalle)}{X}")
    return estado

# Pasos que muestra este script; los del .bat (equipo, descarga, extraccion)
# se suman delante. Ver pasos.py.
TITULOS=["installer.step_environment","installer.step_accelerators",
         "installer.step_manager","installer.step_nodes","installer.step_monitor",
         "installer.step_video","installer.step_interface","installer.step_community","installer.step_verify",
         "installer.step_models","installer.step_launchers"]

def main():
    global RESTRICCIONES_TORCH
    RESTRICCIONES_TORCH=None
    ESTADOS_NODOS.clear()
    os.system("")  # activa los colores ANSI en la consola clasica de Windows 10
    destino=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.getcwd())
    fabricante=sys.argv[2] if len(sys.argv)>2 else None
    variante=sys.argv[3] if len(sys.argv)>3 else None
    py=os.path.join(destino,"python_embeded","python.exe")
    pasos.usar_log(destino)
    P=pasos.Pasos([t(k) for k in TITULOS])
    if not preflight_usuario(destino):
        return 1
    git_en_path()

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
    RESTRICCIONES_TORCH=entorno_torch.restricciones(destino,torch_base)
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

    P.empezar(t("installer.step_manager"))
    manager=ofrecer_manager(destino,py,torch_base)
    P.cerrar(ESTADOS_NODOS.get("manager","ok" if manager else "omitido"),t("installer.step_manager_"+manager) if manager else t("common.not_active"))

    P.empezar(t("installer.step_nodes"))
    nodos_ok=instalar_nodo(destino,py,"cineconia",torch_base)
    P.cerrar(ESTADOS_NODOS.get("cineconia","omitido"),t("installer.installed") if nodos_ok else t("common.not_installed"))

    P.empezar(t("installer.step_monitor"))
    monitor_ok=instalar_nodo(destino,py,"monitor",torch_base)
    P.cerrar(ESTADOS_NODOS.get("monitor","omitido"),t("installer.installed") if monitor_ok else t("common.not_installed"))

    git_en_path()
    for grupo,titulo in (("video","installer.step_video"),("interfaz","installer.step_interface"),
                         ("comunidad","installer.step_community")):
        P.empezar(t(titulo))
        paso_grupo(P,destino,py,grupo,torch_base)
    # Verificar DESPUES de los nodos: sus dependencias pueden afectar aceleradores.
    P.empezar(t("installer.step_verify"))
    proteger_torch(py,torch_base)
    if _presente(py,"triton"):
        ok,msg=catalogo.cabeceras_python(os.path.dirname(py),sys.version_info)
        if msg:
            print(f"   {A if ok else R}{msg}{X}")
    verificados,fallos=verificar(list(catalogo.HERRAMIENTAS),py,solo_presentes=True)
    carpetas=[os.path.basename(ruta_nodo(destino,c)) for c in NODOS if ruta_nodo(destino,c)]
    arranque_ok,detalle=verificacion.comprobar(destino,py,carpetas,manager,RESTRICCIONES_TORCH)
    proteger_torch(py,torch_base)
    problemas=conflictos_pip(py)
    P.cerrar("ok" if arranque_ok and not fallos and not problemas else "fallo",detalle)

    P.empezar(t("installer.step_models"))
    modelos=ofrecer_enlace_modelos(destino)
    P.cerrar("fallo" if modelos=="error" else ("ok" if modelos else "omitido"),t(f"installer.step_models_{modelos or 'none'}"))

    P.empezar(t("installer.step_launchers"))
    creados,preferido=lanzadores.crear_lanzadores(destino,inf,verificados,manager)
    for _,ruta in creados.items():
        print(f"   {pasos.V}{pasos.MARCAS['ok'][0]}{X} {os.path.basename(ruta)}")
    ok,detalle=lanzadores.crear_acceso_escritorio(destino,preferido)
    ajustar_interfaz(destino)
    P.cerrar("ok" if ok else "fallo",t("installer.desktop_shortcut"))

    # Datos del equipo que quedan de referencia, encima del resumen de pasos.
    print(f"\n   {G}Backend: {inf['backend']}  ·  PyTorch: {inf['torch'].get('torch')}  ·  "
          f"{t('installer.main_launcher')}: {os.path.basename(preferido)}{X}")
    if problemas:
        print(f"   {A}{t('installer.pip_conflicts',count=len(problemas))}{X}")
        for linea in problemas[:8]:
            print(f"      {G}{linea}{X}")
    P.resumen()
    incidencias=any(estado=="fallo" for _,estado,_ in P.hechos)
    print(f"\n   {A if incidencias else pasos.V}{t('installer.needs_attention' if incidencias else 'installer.ready')}{X}")
    return 1 if incidencias else 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except entorno_torch.EntornoNoRecuperado as e:
        print(f"\n   {R}{e}{X}")
        pasos.registrar("ERROR PyTorch",str(e))
        sys.exit(1)
