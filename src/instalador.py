"""Adaptive orchestrator: detect, propose, install and verify."""
from __future__ import annotations
import os, subprocess, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import catalogo, deteccion, i18n, lanzadores, modelos_enlace, preflight, rutas_largas

NODOS_REPO="https://github.com/chaLords/ComfyUI-Cine-con-IA.git"
NOMBRES_NODOS=["ComfyUI-Cine-con-IA","ComfyUI-CineConIA","cine-con-ia"]
A,G,R,X="\033[38;5;179m","\033[38;5;245m","\033[38;5;203m","\033[0m"
t=i18n.t

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

def verificar(pasos,py):
    titulo(t("installer.real_verification"))
    verificados=set()
    fallos=[]
    for p in pasos:
        mod=catalogo.HERRAMIENTAS[p["clave"]].get("modulo")
        if not mod:
            verificados.add(p["clave"])
            continue
        try:
            r=subprocess.run(
                [py,"-s","-c",f"import {mod}; print(getattr({mod},'__version__','OK'))"],
                capture_output=True,text=True,timeout=60
            )
        except (OSError,subprocess.SubprocessError) as e:
            fallos.append((p["nombre"],str(e)))
            continue
        if r.returncode==0:
            verificados.add(p["clave"])
            print(f"   {A}{t('common.ok')}{X}   {p['nombre']} {r.stdout.strip()}")
        else:
            linea=(r.stderr.strip().splitlines() or ["error"])[-1]
            fallos.append((p["nombre"],linea[:100]))
            print(f"   {R}{t('installer.import_failed')}{X} {p['nombre']}: {linea[:80]}")
    return verificados,fallos

def instalar_nodos(destino):
    custom=os.path.join(destino,"ComfyUI","custom_nodes")
    if any(os.path.isdir(os.path.join(custom,n)) for n in NOMBRES_NODOS):
        return True
    git=preflight.git_exe()
    if not git:
        return False
    os.makedirs(custom,exist_ok=True)
    if preguntar(
        t("installer.install_nodes"),
        [(t("common.yes"),None),(t("common.no"),None)],1
    )!=1:
        return False
    try:
        return subprocess.run(
            [git,"clone","--depth","1",NODOS_REPO,os.path.join(custom,NOMBRES_NODOS[0])]
        ).returncode==0
    except OSError:
        return False

def ofrecer_enlace_modelos(destino):
    opciones=[
        (t("common.no"),t("installer.search_models_no")),
        (t("common.yes"),t("installer.search_models_yes")),
    ]
    if preguntar(t("installer.search_models"),opciones,1)!=2:
        return
    destino_comfy=os.path.join(destino,"ComfyUI")
    propia=os.path.normcase(os.path.normpath(os.path.join(destino_comfy,"models")))
    encontradas=[
        p for p in modelos_enlace.detectar_instalaciones()
        if os.path.normcase(os.path.normpath(p))!=propia
    ]
    if not encontradas:
        print(f"   {G}{t('installer.no_models_found')}{X}")
        return
    opciones=[(f"{modelos_enlace.tamano_gb(p):.1f} GB - {p}",None) for p in encontradas[:5]]
    opciones.append((t("installer.do_not_link"),None))
    eleccion=preguntar(t("installer.which_models"),opciones,1)
    if eleccion>len(encontradas[:5]):
        return
    ruta,error=modelos_enlace.escribir_yaml(destino_comfy,encontradas[eleccion-1])
    if ruta:
        print(f"   {A}{t('installer.models_linked')}{X}")
    else:
        print(f"   {G}{t('installer.no_changes',error=error)}{X}")

def main():
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
    perfiles=["h3","wan","ltx","sage"] if inf["fabricante"]=="nvidia" else ["h3","wan","ltx"]
    opciones=[
        (t("installer.auto"),t("installer.auto_desc")),
        (t("installer.advanced"),t("installer.advanced_desc")),
    ]
    if preguntar(t("installer.continue"),opciones,1)==2:
        elegidos=elegir_perfiles(inf.get("vram_gb"))
        if elegidos:
            perfiles=elegidos
    herramientas=catalogo.herramientas_de(perfiles)
    verificados=set()
    if herramientas:
        pasos=catalogo.plan(herramientas,inf,f"cp{sys.version_info.major}{sys.version_info.minor}")
        if mostrar_plan(pasos) and preguntar(
            t("installer.install_compatible"),
            [(t("common.yes"),None),(t("common.no"),None)],1
        )==1:
            instalados,omitidos,fallidos=ejecutar(pasos,py)
            verificados,fallos_import=verificar(instalados,py)
            for nombre,motivo in omitidos+fallidos+fallos_import:
                print(f"   {R}{nombre}{X}: {motivo}")
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
    print(f"   {t('installer.nodes')}: {t('common.ok') if nodos_ok else t('common.not_installed')}")
    print(f"   SageAttention: {t('common.ok') if 'sageattention' in verificados else t('common.not_active')}")
    print(f"   FlashAttention: {t('common.ok') if 'flashattention' in verificados else t('common.not_active')}")
    print(f"   Nunchaku: {t('common.ok') if 'nunchaku' in verificados else t('common.not_active')}")
    return 0

if __name__=="__main__":
    sys.exit(main())
