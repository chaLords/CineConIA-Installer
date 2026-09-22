"""El límite de 260 caracteres de Windows, que rompe instalaciones enteras.

Windows corta las rutas en 260 caracteres salvo que se active una opción
del registro. ComfyUI anida mucho —`custom_nodes/<paquete>/<subcarpeta>/...`—
y algunos paquetes traen archivos con nombres largos, así que el límite se
alcanza de verdad y el fallo que aparece no se parece en nada a su causa:
"no se encuentra el archivo", con el archivo delante.

Este módulo solo LEE el estado. Cambiarlo toca el registro y pide permisos
de administrador, así que no se hace por sorpresa: se detecta, se explica y
se da el comando para que lo ejecute quien quiera, a sabiendas.
"""
import subprocess
import i18n

CLAVE = r"HKLM\SYSTEM\CurrentControlSet\Control\FileSystem"
VALOR = "LongPathsEnabled"

COMANDO = (
    'powershell -Command "Start-Process powershell -Verb RunAs '
    "-ArgumentList 'New-ItemProperty -Path \\\"HKLM:\\SYSTEM\\CurrentControlSet"
    "\\Control\\FileSystem\\\" -Name LongPathsEnabled -Value 1 -PropertyType "
    "DWORD -Force'\""
)


def estado():
    """True si las rutas largas están activas, False si no, None si no se sabe."""
    try:
        r = subprocess.run(["reg", "query", CLAVE, "/v", VALOR],
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return False          # el valor no existe = desactivado
    for linea in r.stdout.splitlines():
        if VALOR.lower() in linea.lower():
            # "    LongPathsEnabled    REG_DWORD    0x1"
            trozo = linea.split()[-1]
            try:
                return int(trozo, 16 if trozo.lower().startswith("0x") else 10) == 1
            except ValueError:
                return None
    return None


def aviso():
    """Localized warning, or None when there is nothing to report."""
    e = estado()
    if e is True or e is None:
        return None
    return i18n.t("longpaths.warning", command=COMANDO)
