"""Adaptive orchestrator: detect, propose, install and verify."""
from __future__ import annotations
import os, subprocess, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import catalogo, deteccion, i18n, lanzadores, modelos_enlace, preflight, rutas_largas

NODOS_REPO="https://github.com/chaLords/ComfyUI-Cine-con-IA.git"
NOMBRES_NODOS=["ComfyUI-Cine-con-IA","ComfyUI-CineConIA","cine-con-ia"]
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
    titulo(t("installer.detected_environment"))
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

def mostrar_plan(pasos):
    titulo(t("installer.accelerator_plan"))
    n=0
    for p in pasos:
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
    print(f"\n{A}>> {nombre}{X}")
    try:
        return subprocess.run(
            [py,"-s","-m","pip","install","--no-cache-dir","--timeout","600","--retries","5"]+args
        ).returncode==0
    except OSError:
        return False

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

def ofrecer_manager(destino,py):
    """ComfyUI-Manager instala los nodos que falten al abrir un workflow."""
    req=os.path.join(destino,"ComfyUI","manager_requirements.txt")
    if not lanzadores.flag_soportado(destino,"--enable-manager"):
        return False
    if lanzadores.manager_disponible(destino):
        return True
    if not os.path.isfile(req):
        return False
    titulo("ComfyUI-Manager")
    print("   "+t("installer.manager_desc"))
    if preguntar(t("installer.install_manager"),SI_NO(),1)!=1:
        return False
    pip_instalar(py,["-r",req],"ComfyUI-Manager")
    return lanzadores.manager_disponible(destino)

def instalar_nodos(destino):
    custom=os.path.join(destino,"ComfyUI","custom_nodes")
    if any(os.path.isdir(os.path.join(custom,n)) for n in NOMBRES_NODOS):
        return True
    git=preflight.git_exe()
    if not git:
        return False
    os.makedirs(custom,exist_ok=True)
    if preguntar(t("installer.install_nodes"),SI_NO(),1)!=1:
        return False
    try:
        return subprocess.run(
            [git,"clone","--depth","1",NODOS_REPO,os.path.join(custom,NOMBRES_NODOS[0])]
        ).returncode==0
    except OSError:
        return False

def ofrecer_enlace_modelos(destino):
    """Busca modelos de instalaciones anteriores y solo pregunta si encuentra algo."""
    destino_comfy=os.path.join(destino,"ComfyUI")
    real=lambda p:os.path.normcase(os.path.realpath(p))
    propia=real(os.path.join(destino_comfy,"models"))
    titulo(t("installer.models_title"))
    print(f"   {G}{t('installer.searching_models')}{X}")
    encontradas=[p for p in modelos_enlace.detectar_instalaciones() if real(p)!=propia]
    con_tamano=[(p,modelos_enlace.tamano_gb(p)) for p in encontradas]
    con_tamano=sorted([x for x in con_tamano if x[1]>0],key=lambda x:-x[1])[:5]
    if not con_tamano:
        print(f"   {G}{t('installer.no_models_found')}{X}")
        return
    print("   "+t("installer.models_found"))
    opciones=[(f"{gb:.1f} GB - {p}",None) for p,gb in con_tamano]
    opciones.append((t("installer.do_not_link"),t("installer.search_models_no")))
    eleccion=preguntar(t("installer.which_models"),opciones,1)
    if eleccion>len(con_tamano):
        return
    models=con_tamano[eleccion-1][0]
    try:
        _,backup=modelos_enlace.actualizar_yaml(destino_comfy,models,modelos_enlace.mapa_categorias(models))
    except OSError as e:
        print(f"   {R}{t('installer.no_changes',error=e)}{X}")
        return
    print(f"   {A}{t('installer.models_linked')}{X}")
    if backup:
        print(f"   {G}{backup}{X}")
    print(f"   {G}{t('installer.migrator_hint')}{X}")

def main():
    os.system("")  # activa los colores ANSI en la consola clasica de Windows 10
    destino=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.getcwd())
    fabricante=sys.argv[2] if len(sys.argv)>2 else None
    variante=sys.argv[3] if len(sys.argv)>3 else None
    py=os.path.join(destino,"python_embeded","python.exe")
    if not preflight_usuario(destino):
        return 1
    inf=deteccion.informe(py,destino,fabricante,variante)
    mostrar_equipo(inf)
    if not inf["torch"].get("torch"):
        print(f"\n   {R}{t('installer.pytorch_broken')}{X}")
        return 1
    if not gpu_utilizable(inf):
        return 1
    perfiles=["sage"] if inf["fabricante"]=="nvidia" and not inf.get("gpu_inutilizable") else []
    opciones=[
        (t("installer.auto"),t("installer.auto_desc")),
        (t("installer.advanced"),t("installer.advanced_desc")),
    ]
    if preguntar(t("installer.continue"),opciones,1)==2:
        perfiles=elegir_perfiles(inf.get("vram_gb"))
    herramientas=catalogo.herramientas_de(perfiles)
    if herramientas:
        pasos=catalogo.plan(herramientas,inf,f"cp{sys.version_info.major}{sys.version_info.minor}")
        if mostrar_plan(pasos) and preguntar(t("installer.install_compatible"),SI_NO(),1)==1:
            _,omitidos,fallidos=ejecutar(pasos,py)
            for nombre,motivo in omitidos+fallidos:
                print(f"   {R}{nombre}{X}: {motivo}")
    # Se verifica todo lo que haya, instalado ahora o en una ejecucion anterior:
    # asi repetir el instalador nunca degrada el acceso directo.
    titulo(t("installer.real_verification"))
    verificados,_=verificar(list(catalogo.HERRAMIENTAS),py,solo_presentes=True)
    manager_ok=ofrecer_manager(destino,py)
    nodos_ok=instalar_nodos(destino)
    ofrecer_enlace_modelos(destino)
    titulo(t("installer.creating_launchers"))
    creados,preferido=lanzadores.crear_lanzadores(destino,inf,verificados)
    for _,ruta in creados.items():
        print(f"   {A}{t('common.ok')}{X} {os.path.basename(ruta)}")
    ok,detalle=lanzadores.crear_acceso_escritorio(destino,preferido)
    print(f"   {t('common.ok') if ok else t('common.failed')} {t('installer.desktop_shortcut')}")
    titulo(t("installer.summary"))
    print(f"   Backend: {inf['backend']}")
    print(f"   {t('installer.main_launcher')}: {os.path.basename(preferido)}")
    print(f"   ComfyUI-Manager: {t('common.ok') if manager_ok else t('common.not_active')}")
    print(f"   {t('installer.nodes')}: {t('common.ok') if nodos_ok else t('common.not_installed')}")
    print(f"   SageAttention: {t('common.ok') if 'sageattention' in verificados else t('common.not_active')}")
    print(f"   FlashAttention: {t('common.ok') if 'flashattention' in verificados else t('common.not_active')}")
    print(f"   Nunchaku: {t('common.ok') if 'nunchaku' in verificados else t('common.not_active')}")
    print(f"\n   {A}{t('installer.ready')}{X}")
    return 0

if __name__=="__main__":
    sys.exit(main())
