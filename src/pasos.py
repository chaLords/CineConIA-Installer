"""Pasos numerados de la instalacion y el resumen final.

Cada paso abre con "[n/T] titulo" y cierra con una linea propia: visto verde,
guion gris (omitido) o cruz roja. Los comandos largos (pip, git) corren con un
indicador que se borra al terminar y su salida va a _cineconia/instalacion.log,
asi no quedan en pantalla barras de otros programas congeladas a la mitad.

Los pasos del .bat (equipo, descarga, extraccion) llegan por variables de
entorno CIA_PASOS_BAT y CIA_PASO1..n ("titulo|detalle") y entran al resumen.
"""
from __future__ import annotations
import os, subprocess, sys, time
import i18n

A, G, R, V, X = "\033[38;5;179m", "\033[38;5;245m", "\033[38;5;203m", "\033[38;5;71m", "\033[0m"
# Windows Terminal dibuja los simbolos; la consola clasica de Windows 10 no siempre.
_WT = bool(os.environ.get("WT_SESSION"))
MARCAS = {"ok": ("\u2713" if _WT else "OK", V), "omitido": ("\u2013" if _WT else "-", G),
          "fallo": ("\u2717" if _WT else "X", R)}
GIRO = "|/-\\"
ANCHO = 40
_log = {"ruta": None}


def usar_log(destino):
    """El registro completo de pip y git va a <destino>/_cineconia/instalacion.log."""
    carpeta = os.path.join(destino, "_cineconia")
    try:
        os.makedirs(carpeta, exist_ok=True)
        _log["ruta"] = os.path.join(carpeta, "instalacion.log")
    except OSError:
        _log["ruta"] = None
    return _log["ruta"]


def duracion(segundos):
    s = int(max(0, segundos))
    return f"{s // 60} min {s % 60:02d} s" if s >= 60 else f"{s} s"


def _cola(texto, n=6):
    lineas = [l for l in (texto or "").splitlines() if l.strip()]
    return lineas[-n:]


def registrar(etiqueta, texto):
    """Agrega texto al registro de la instalacion, si hay uno."""
    if _log["ruta"]:
        try:
            with open(_log["ruta"], "a", encoding="utf-8") as f:
                f.write(f"\n===== {etiqueta}\n{texto}")
        except OSError:
            pass


def correr(cmd, etiqueta, entorno=None, cwd=None, timeout=None, completo=False):
    """Ejecuta cmd mostrando un indicador en una sola linea. (ok, ultimas lineas)."""
    salida = []
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", PIP_PROGRESS_BAR="off", **(entorno or {}))
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, env=env, text=True,
                             encoding="utf-8", errors="replace", cwd=cwd)
    except OSError as e:
        return False, [str(e)]
    import threading
    hilo = threading.Thread(target=lambda: salida.extend(p.stdout), daemon=True)
    hilo.start()
    t0, i = time.time(), 0
    while p.poll() is None:
        if timeout is not None and time.time()-t0>timeout:
            p.kill()
            p.wait()
            salida.append("\nTIMEOUT: " + etiqueta + "\n")
            break
        seg = int(time.time() - t0)
        sys.stdout.write(f"\r   {A}{GIRO[i % 4]}{X} {etiqueta}  {G}{seg // 60}:{seg % 60:02d}{X}   ")
        sys.stdout.flush()
        time.sleep(0.2)
        i += 1
    hilo.join(timeout=5)
    p.stdout.close()
    sys.stdout.write("\r\033[2K")
    sys.stdout.flush()
    texto = "".join(salida)
    if _log["ruta"]:
        try:
            with open(_log["ruta"], "a", encoding="utf-8") as f:
                f.write(f"\n===== {etiqueta} :: {' '.join(map(str, cmd))}\n{texto}")
        except OSError:
            pass
    return p.returncode == 0, (texto.splitlines() if completo else _cola(texto))


class Pasos:
    def __init__(self, titulos):
        self.hechos = []
        for i in range(1, int(os.environ.get("CIA_PASOS_BAT") or 0) + 1):
            titulo, _, detalle = (os.environ.get(f"CIA_PASO{i}") or "").partition("|")
            if titulo:
                self.hechos.append((titulo, "ok", detalle))
        self.n = len(self.hechos)
        self.total = self.n + len(titulos)
        self.actual = None
        try:
            self.inicio = float(os.environ.get("CIA_INICIO") or time.time())
        except ValueError:
            self.inicio = time.time()

    def empezar(self, titulo):
        self.n += 1
        self.actual = titulo
        print(f"\n{A}[{self.n}/{self.total}] {titulo}{X}")

    def _linea(self, titulo, estado, detalle, numero=None):
        marca, color = MARCAS[estado]
        num = f"[{numero}/{self.total}] " if numero else ""
        puntos = "." * max(3, ANCHO + 8 - len(num + titulo))
        return f"   {color}{num}{titulo} {G}{puntos}{X} {color}{marca}{X} {detalle}".rstrip()

    def cerrar(self, estado="ok", detalle=""):
        if self.actual is None:
            return
        print(self._linea(self.actual, estado, detalle, self.n))
        self.hechos.append((self.actual, estado, detalle))
        self.actual = None

    def resumen(self):
        t = i18n.t
        fallos = sum(1 for _, e, _ in self.hechos if e == "fallo")
        barra = "=" * 58
        print(f"\n{A}{barra}{X}")
        for i, (titulo, estado, detalle) in enumerate(self.hechos, 1):
            print(self._linea(titulo, estado, detalle, i))
        tiempo = duracion(time.time() - self.inicio)
        marca, color = MARCAS["fallo" if fallos else "ok"]
        clave = "installer.done_with_issues" if fallos else "installer.done_in"
        print(f"{A}{barra}{X}")
        print(f"   {color}{marca} {t(clave, time=tiempo)}{X}")
        if _log["ruta"]:
            print(f"   {G}{t('installer.log_hint', path=_log['ruta'])}{X}")
        print(f"{A}{barra}{X}")
