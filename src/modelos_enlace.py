"""Reutilizar modelos que ya están en el disco, sin copiarlos.

Este instalador no descarga modelos. Pero mucha gente ya tiene decenas de
gigas de otra instalación de ComfyUI, y volver a bajarlos es absurdo.

ComfyUI trae un mecanismo oficial para esto, `extra_model_paths.yaml`: se
le dicen carpetas adicionales donde buscar y las lee como si fueran suyas.
Es mejor que los enlaces simbólicos, que en Windows piden permisos de
administrador y se rompen al mover carpetas.
"""
import os

#: Las subcarpetas que ComfyUI reconoce. Si la instalación de origen tiene
#: alguna, se anota; las que no existan no se escriben, para no llenar el
#: archivo de rutas muertas.
CARPETAS = [
    "checkpoints", "diffusion_models", "unet", "text_encoders", "clip",
    "clip_vision", "vae", "loras", "controlnet", "upscale_models",
    "embeddings", "hypernetworks", "style_models", "gligen",
    "latent_upscale_models", "frame_interpolation", "vae_approx",
]


#: Carpetas que no hace falta mirar y que engordan la busqueda.
IGNORAR = {"$recycle.bin", "windows", "program files", "program files (x86)",
           "programdata", "appdata", "node_modules", ".git", "system volume information",
           "python_embeded", "custom_nodes", "venv", "site-packages"}


def detectar_instalaciones(profundidad=5):
    """Busca carpetas 'models' de ComfyUI en los sitios habituales.

    Con rutas fijas no basta: la gente anida ComfyUI de formas que no se
    pueden enumerar (ComfyUI/ComfyUI-Easy-Install/ComfyUI/models es real).
    Se recorre por profundidad limitada, saltando lo que nunca contiene
    modelos, para no tardar minutos ni encontrar basura.
    """
    candidatos, vistos = [], set()
    raices = [os.path.expanduser("~/Documents"), os.path.expanduser("~/Desktop"),
              "C:/", "D:/", "E:/"]

    def mirar(carpeta, nivel):
        if nivel > profundidad:
            return
        try:
            entradas = list(os.scandir(carpeta))
        except OSError:
            return
        for e in entradas:
            if not e.is_dir(follow_symlinks=False):
                continue
            nombre = e.name.lower()
            if nombre in IGNORAR or nombre.startswith("."):
                continue
            if nombre == "models":
                real = os.path.normpath(e.path)
                if real not in vistos and any(
                        os.path.isdir(os.path.join(real, c)) for c in CARPETAS):
                    vistos.add(real)
                    candidatos.append(real)
                continue          # dentro de models ya no hay que seguir
            mirar(e.path, nivel + 1)

    for raiz in raices:
        if os.path.isdir(raiz):
            mirar(raiz, 1)
    return candidatos


def tamano_gb(carpeta):
    """Cuánto ocupa, solo mirando el primer nivel de cada subcarpeta."""
    total = 0
    for c in CARPETAS:
        d = os.path.join(carpeta, c)
        if not os.path.isdir(d):
            continue
        try:
            for e in os.scandir(d):
                if e.is_file():
                    total += e.stat().st_size
        except OSError:
            continue
    return round(total / 1e9, 1)


def escribir_yaml(destino_comfyui, carpeta_modelos):
    """Deja el extra_model_paths.yaml apuntando a la carpeta indicada.

    Si ya existe uno, no se pisa: se avisa y se deja intacto. Sobrescribir
    la configuración de alguien sin preguntar es exactamente lo que no debe
    hacer un instalador.
    """
    ruta = os.path.join(destino_comfyui, "extra_model_paths.yaml")
    if os.path.exists(ruta):
        return None, f"ya existe {ruta}; no se toca"

    base = carpeta_modelos.replace("\\", "/")
    lineas = ["# Escrito por el instalador de Cine con IA.",
              "# Apunta a modelos que ya estaban en el disco: no se copió nada.",
              "otra_instalacion:",
              f"    base_path: {base}",
              ""]
    for c in CARPETAS:
        if os.path.isdir(os.path.join(carpeta_modelos, c)):
            lineas.append(f"    {c}: {c}")
    try:
        with open(ruta, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lineas) + "\n")
    except OSError as e:
        return None, str(e)
    return ruta, None
