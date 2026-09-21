"""Orquestador adaptativo: detecta, propone, instala y verifica."""
from __future__ import annotations
import os, subprocess, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import catalogo, deteccion, lanzadores, modelos_enlace, preflight, rutas_largas

NODOS_REPO="https://github.com/chaLords/ComfyUI-Cine-con-IA.git"
NOMBRES_NODOS=["ComfyUI-Cine-con-IA","ComfyUI-CineConIA","cine-con-ia"]
A,G,R,X="\033[38;5;179m","\033[38;5;245m","\033[38;5;203m","\033[0m"

def titulo(t): print(f"\n{A}{'='*62}\n  {t}\n{'='*62}{X}")

def preguntar(texto,opciones,defecto=1):
    for i,(e,x) in enumerate(opciones,1):
        print(f"   {i}) {e}{' '+A+'(recomendado)'+X if i==defecto else ''}")
        if x: print(f"      {G}{x}{X}")
    while True:
        r=input(f"\n   {texto} [{defecto}]: ").strip()
        if not r: return defecto
        if r.isdigit() and 1<=int(r)<=len(opciones): return int(r)

def marcar(texto,opciones):
    for i,(e,x) in enumerate(opciones,1):
        print(f"   {i}) {e}")
        if x: print(f"      {G}{x}{X}")
    r=input(f"\n   {texto} (ej. 1,3; Enter=ninguna): ").strip()
    if not r: return []
    return [int(x) for x in r.replace(","," ").split() if x.isdigit() and 1<=int(x)<=len(opciones)]

def mostrar_equipo(inf):
    titulo("Entorno detectado")
    print(f"   GPU        {inf['gpu']}")
    if inf.get("vram_gb") is not None: print(f"   VRAM       {inf['vram_gb']} GB")
    print(f"   Fabricante {inf['fabricante']}")
    print(f"   Backend    {inf['backend']}")
    print(f"   PyTorch    {inf['torch'].get('torch') or 'NO DISPONIBLE'}")
    print(f"   Python     {inf['python']}")
    print(f"   Espacio    {inf['espacio_gb']} GB libres")

def preflight_usuario(destino):
    sano,faltan=preflight.salud_comfyui(destino)
    if not sano:
        titulo("Instalacion incompleta"); print(f"   {R}{', '.join(faltan)}{X}"); return False
    aviso=rutas_largas.aviso()
    if aviso:
        titulo("Rutas largas de Windows"); print("   "+aviso)
    if not preflight.git_exe():
        titulo("Git")
        print("   Git hace falta para instalar y actualizar nodos.")
        if preflight.winget_exe() and preguntar("Instalar Git con winget?",[("Si",None),("No","Se omitiran los nodos")],1)==1:
            ok,msg=preflight.instalar_git(); print(f"   {A if ok else R}{msg}{X}")
    return True

def elegir_perfiles(vram):
    claves=list(catalogo.PERFILES); opts=[]
    for c in claves:
        p=catalogo.PERFILES[c]; aviso=""
        if vram and p["vram_min"]>vram: aviso=f" [~{p['vram_min']} GB; tienes {vram}]"
        opts.append((p["nombre"]+aviso,p["detalle"]))
    return [claves[i-1] for i in marcar("Marca los extras",opts)]

def mostrar_plan(pasos):
    titulo("Plan de aceleradores"); n=0
    for p in pasos:
        print(f"\n   {A}{p['nombre']}{X}")
        if p["url"]: print("      wheel: "+os.path.basename(p["url"])); n+=1
        elif p["spec"]: print("      pip:   "+p["spec"]); n+=1
        if p["aviso"]: print(f"      {R}OMITIDO: {p['aviso']}{X}")
        print(f"      {G}{p['licencia']}{X}")
    return n

def pip_instalar(py,args,nombre):
    print(f"\n{A}>> {nombre}{X}")
    try:
        return subprocess.run([py,"-s","-m","pip","install","--no-cache-dir","--timeout","600","--retries","5"]+args).returncode==0
    except OSError: return False

def ejecutar(pasos,py):
    ok,omit,fail=[],[],[]
    for p in pasos:
        if not p["url"] and not p["spec"]:
            omit.append((p["nombre"],p["aviso"] or "sin paquete compatible")); continue
        destino=[p["url"]] if p["url"] else [p["spec"]]
        if pip_instalar(py,destino,p["nombre"]): ok.append(p)
        else: fail.append((p["nombre"],"pip devolvio error"))
    return ok,omit,fail

def verificar(pasos,py):
    titulo("Verificacion real"); ver=set(); fallos=[]
    for p in pasos:
        mod=catalogo.HERRAMIENTAS[p["clave"]].get("modulo")
        if not mod: ver.add(p["clave"]); continue
        try:
            r=subprocess.run([py,"-s","-c",f"import {mod}; print(getattr({mod},'__version__','OK'))"],capture_output=True,text=True,timeout=60)
        except (OSError,subprocess.SubprocessError) as e:
            fallos.append((p["nombre"],str(e))); continue
        if r.returncode==0:
            ver.add(p["clave"]); print(f"   {A}OK{X}   {p['nombre']} {r.stdout.strip()}")
        else:
            linea=(r.stderr.strip().splitlines() or ["error"])[-1]
            fallos.append((p["nombre"],linea[:100])); print(f"   {R}FALLA{X} {p['nombre']}: {linea[:80]}")
    return ver,fallos

def instalar_nodos(destino):
    custom=os.path.join(destino,"ComfyUI","custom_nodes")
    if any(os.path.isdir(os.path.join(custom,n)) for n in NOMBRES_NODOS): return True
    git=preflight.git_exe()
    if not git: return False
    os.makedirs(custom,exist_ok=True)
    if preguntar("Instalar nodos Cine con IA?",[("Si",None),("No",None)],1)!=1: return False
    try: return subprocess.run([git,"clone","--depth","1",NODOS_REPO,os.path.join(custom,NOMBRES_NODOS[0])]).returncode==0
    except OSError: return False

def ofrecer_enlace_modelos(destino):
    if preguntar("Buscar modelos de otra instalacion?",
                 [("No","No toca carpetas existentes"),
                  ("Si","Busca con limites y enlaza sin copiar")],1)!=2:
        return
    destino_comfy=os.path.join(destino,"ComfyUI")
    propia=os.path.normcase(os.path.normpath(os.path.join(destino_comfy,"models")))
    encontradas=[p for p in modelos_enlace.detectar_instalaciones()
                 if os.path.normcase(os.path.normpath(p))!=propia]
    if not encontradas:
        print(f"   {G}No encontre otra carpeta de modelos.{X}")
        return
    opciones=[(f"{modelos_enlace.tamano_gb(p):.1f} GB - {p}",None) for p in encontradas[:5]]
    opciones.append(("No enlazar nada",None))
    eleccion=preguntar("Cual usar?",opciones,1)
    if eleccion>len(encontradas[:5]):
        return
    ruta,error=modelos_enlace.escribir_yaml(destino_comfy,encontradas[eleccion-1])
    if ruta:
        print(f"   {A}Modelos enlazados sin copiar archivos.{X}")
    else:
        print(f"   {G}No se modifico nada: {error}{X}")

def main():
    destino=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.getcwd())
    fabricante=sys.argv[2] if len(sys.argv)>2 else None
    variante=sys.argv[3] if len(sys.argv)>3 else None
    py=os.path.join(destino,"python_embeded","python.exe")
    if not preflight_usuario(destino): return 1
    inf=deteccion.informe(py,destino,fabricante,variante); mostrar_equipo(inf)
    if not inf["torch"].get("torch"):
        print(f"\n   {R}PyTorch no funciona; no instalare extras encima de un entorno roto.{X}"); return 1
    perfiles=["h3","wan","ltx","sage"] if inf["fabricante"]=="nvidia" else ["h3","wan","ltx"]
    if preguntar("Continuar?",[("Configuracion automatica","La opcion segura"),("Modo avanzado","Elegir Nunchaku, Flash, etc.")],1)==2:
        elegidos=elegir_perfiles(inf.get("vram_gb"))
        if elegidos: perfiles=elegidos
    herramientas=catalogo.herramientas_de(perfiles); verificados=set()
    if herramientas:
        pasos=catalogo.plan(herramientas,inf,f"cp{sys.version_info.major}{sys.version_info.minor}")
        if mostrar_plan(pasos) and preguntar("Instalar compatibles?",[("Si",None),("No",None)],1)==1:
            instalados,omitidos,fallidos=ejecutar(pasos,py)
            verificados,fallos_import=verificar(instalados,py)
            for nombre,motivo in omitidos+fallidos+fallos_import: print(f"   {R}{nombre}{X}: {motivo}")
    nodos_ok=instalar_nodos(destino)
    ofrecer_enlace_modelos(destino)
    titulo("Creando lanzadores")
    creados,preferido=lanzadores.crear_lanzadores(destino,inf,verificados)
    for _,ruta in creados.items(): print(f"   {A}OK{X} {os.path.basename(ruta)}")
    ok,detalle=lanzadores.crear_acceso_escritorio(destino,preferido)
    print(f"   {'OK' if ok else 'FALLO'} acceso de escritorio ComfyUI")
    titulo("Resumen")
    print(f"   Backend: {inf['backend']}")
    print(f"   Lanzador principal: {os.path.basename(preferido)}")
    print(f"   Nodos Cine con IA: {'OK' if nodos_ok else 'no instalados'}")
    print(f"   SageAttention: {'OK' if 'sageattention' in verificados else 'no activo'}")
    print(f"   FlashAttention: {'OK' if 'flashattention' in verificados else 'no activo'}")
    print(f"   Nunchaku: {'OK' if 'nunchaku' in verificados else 'no activo'}")
    return 0

if __name__=="__main__":
    sys.exit(main())
