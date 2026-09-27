"""Barra de progreso de una sola linea para trabajos largos con archivos.

La migracion lee cada modelo varias veces (copiar, SHA-256 del origen y de la
copia, verificar otra vez antes de borrar) y un modelo de video puede pesar
20 GB: sin un indicador la consola parece congelada.

- Una linea que se redibuja con \\r: barra, porcentaje, GB hechos, tiempo que
  falta, velocidad, que se esta haciendo y con que archivo. Se ajusta al ancho
  de la ventana.
- El porcentaje tambien va al titulo de la ventana y, en Windows Terminal, al
  anillo de progreso de la pestana y del icono en la barra de tareas (OSC 9;4).
- Fuera de una consola (pruebas, salida redirigida a un archivo) no dibuja
  nada en vivo: solo la linea final con el resumen.
- CINECONIA_PROGRESO=0 desactiva la linea en vivo.

Progreso es para trabajos con total conocido (bytes). Actividad dibuja la
misma linea para lo que no tiene total (pip, git, pruebas de arranque): un
tramo ambar recorre la barra y en lugar del porcentaje va el tiempo. La
descarga, el SHA-256 y la extraccion del .bat usan la misma linea desde
progreso.ps1, que copia este formato.
"""
from __future__ import annotations

import os
import shutil
import sys
import threading
import time
import unicodedata

import i18n
import pasos

t = i18n.t
_WT = bool(os.environ.get("WT_SESSION"))
LLENO, VACIO = "█", "░"          # bloques completos y sombreados
PUNTOS = "…" if _WT else "..."
SEP = " · "
REFRESCO = 0.2        # segundos minimos entre dibujos
ARCHIVO_GRANDE = 256 * 1024 * 1024  # desde aqui se muestra el % del archivo


def _es_consola(salida):
    if os.environ.get("CINECONIA_PROGRESO", "").strip() == "0":
        return False
    try:
        return bool(salida.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def _activar_vt():
    """Colores y secuencias ANSI tambien en la consola clasica de Windows 10."""
    if os.name != "nt":
        return True
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        modo = ctypes.c_uint32()
        if not k.GetConsoleMode(h, ctypes.byref(modo)):
            return False
        if modo.value & 0x0004:
            return True
        return bool(k.SetConsoleMode(h, modo.value | 0x0004))
    except Exception:
        return False


def _titulo_consola(nuevo=None):
    """Lee el titulo de la ventana o lo cambia. Solo Windows."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        k = ctypes.windll.kernel32
        if nuevo is not None:
            k.SetConsoleTitleW(str(nuevo))
            return None
        buf = ctypes.create_unicode_buffer(1024)
        return buf.value if k.GetConsoleTitleW(buf, 1024) else None
    except Exception:
        return None


def ancho_texto(s):
    """Columnas que ocupa s en la consola (CJK cuenta doble)."""
    n = 0
    for c in s:
        if unicodedata.combining(c):
            continue
        n += 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
    return n


def recortar_medio(s, ancho):
    """Recorta por el medio: el final del nombre (fp16, .safetensors) importa."""
    if ancho_texto(s) <= ancho:
        return s
    if ancho <= len(PUNTOS):
        return PUNTOS[:max(0, ancho)]
    resto = ancho - len(PUNTOS)
    cabeza_max, cola_max = resto // 2, resto - resto // 2
    cabeza, w = [], 0
    for c in s:
        cw = ancho_texto(c)
        if w + cw > cabeza_max:
            break
        cabeza.append(c)
        w += cw
    cola, w = [], 0
    for c in reversed(s):
        cw = ancho_texto(c)
        if w + cw > cola_max:
            break
        cola.append(c)
        w += cw
    return "".join(cabeza) + PUNTOS + "".join(reversed(cola))


def _unidad(n):
    for unidad, factor in (("TB", 1024 ** 4), ("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if n >= factor:
            return unidad, factor
    return "B", 1


def tamano_par(hecho, total):
    """'40.1 / 71.8 GB': las dos cifras en la unidad del total."""
    unidad, f = _unidad(total)
    dec = 0 if unidad in ("B", "KB") else 1
    return f"{hecho / f:.{dec}f} / {total / f:.{dec}f} {unidad}"


def velocidad(bps):
    unidad, f = _unidad(max(bps, 1024 ** 2))
    v = bps / f
    return f"{v:.0f} {unidad}/s" if v >= 10 else f"{v:.1f} {unidad}/s"


def tiempo_restante(seg):
    s = int(max(0, seg))
    if s < 60:
        return f"{max(5, (s + 4) // 5 * 5)} s"
    if s < 600:
        m, r = divmod(s, 60)
        return f"{m} min {r // 10 * 10:02d} s"
    if s < 3600:
        return f"{(s + 30) // 60} min"
    h, r = divmod(s, 3600)
    return f"{h} h {r // 60:02d} min"


def ancho_barra(util):
    """Ancho fijo de la barra: si cambiara con cada dibujo, la linea bailaria."""
    return 20 if util >= 90 else 12


class _Linea:
    """Lo comun a Progreso y Actividad: una linea viva al pie de la consola."""

    def _iniciar_linea(self, salida, sangria):
        self.salida = salida or sys.stdout
        self.vivo = _es_consola(self.salida)
        self.vt = self.vivo and _activar_vt()
        self.sangria = sangria
        self._visible = False
        self._cerrado = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cerrar()
        return False

    def _c(self, texto, color):
        return f"{color}{texto}{pasos.X}" if self.vt and texto else texto

    def _borrar(self):
        if not self._visible:
            return
        if self.vt:
            self.salida.write("\r\033[2K")
        else:
            ancho = shutil.get_terminal_size((100, 24)).columns
            self.salida.write("\r" + " " * max(0, ancho - 1) + "\r")
        self.salida.flush()
        self._visible = False

    def _pestana(self, estado, pct=0):
        """Anillo de la pestana y del icono en la barra de tareas de Windows
        Terminal: 1 = porcentaje, 3 = en curso sin total, 0 = quitar."""
        if _WT and self.vt:
            return f"\033]9;4;{estado};{pct}\a"
        return ""

    def _escribir_linea(self, plano, coloreado, ancho, extra=""):
        if self.vt:
            self.salida.write("\r" + coloreado + "\033[K" + extra)
        else:
            relleno = max(0, ancho - 1 - ancho_texto(plano))
            self.salida.write("\r" + plano + " " * relleno)
        self.salida.flush()
        self._visible = True

    def escribir(self, texto=""):
        """Imprime una linea de registro por encima de la barra."""
        self._borrar()
        print(texto, file=self.salida)
        self.salida.flush()


class Progreso(_Linea):
    """Avance de una fase: se miden bytes de la biblioteca, no lecturas.

    Cada archivo declara cuanto trabajo lleva (p. ej. 3 x tamano: copiar,
    SHA-256 del origen y de la copia) y avanzar() suma bytes leidos o escritos.
    En pantalla se ve tamano x fraccion hecha, asi "40 / 72 GB" y los MB/s
    hablan de la biblioteca real y no de cuantas veces se leyo.
    """

    def __init__(self, total_bytes, total_archivos, titulo="", sangria="   ",
                 mostrar_nombre=True, por_bytes=True, salida=None):
        self._iniciar_linea(salida, sangria)
        self.total = max(0, int(total_bytes or 0))
        self.n = max(0, int(total_archivos or 0))
        self.titulo = titulo
        self.mostrar_nombre = mostrar_nombre
        self.por_bytes = por_bytes and self.total > 0
        self.base = 0
        self.hechos = 0
        self.i = 0
        self.nombre = ""
        self.accion = ""
        self.tam = 0
        self.trabajo = 0
        self.trabajo_hecho = 0
        self.t0 = time.monotonic()
        self._muestra = (self.t0, 0.0)
        self.vel = None
        self._ultimo = 0.0
        self._pct_titulo = None
        self._titulo_original = _titulo_consola() if self.vivo else None

    # -- estado -----------------------------------------------------------
    def _parcial(self):
        if self.trabajo <= 0:
            return 0.0
        return min(1.0, self.trabajo_hecho / self.trabajo)

    def procesado(self):
        return self.base + self.tam * self._parcial()

    def fraccion(self):
        if self.por_bytes:
            return min(1.0, self.procesado() / self.total)
        if self.n:
            return min(1.0, (self.hechos + self._parcial()) / self.n)
        return 1.0

    def transcurrido(self):
        return time.monotonic() - self.t0

    def archivo(self, i, nombre, tamano, trabajo, accion):
        """Empieza el archivo i. trabajo: bytes que se van a leer/escribir."""
        self.i, self.nombre, self.accion = i, nombre, accion
        self.tam = max(0, int(tamano or 0))
        self.trabajo = max(0, int(trabajo or 0))
        self.trabajo_hecho = 0
        self._dibujar(forzar=True)

    def fase(self, accion):
        """Cambia lo que se muestra que se esta haciendo con el archivo."""
        self.accion = accion
        self._dibujar(forzar=True)

    def avanzar(self, n):
        self.trabajo_hecho += n
        self._dibujar()

    def terminar_archivo(self):
        self.base += self.tam
        self.hechos += 1
        self.tam = self.trabajo = self.trabajo_hecho = 0

    # -- pantalla ---------------------------------------------------------
    def _medir(self, ahora):
        t_prev, p_prev = self._muestra
        dt = ahora - t_prev
        if dt < 0.5:
            return
        p = self.procesado()
        inst = max(0.0, (p - p_prev) / dt)
        self.vel = inst if self.vel is None else 0.3 * inst + 0.7 * self.vel
        self._muestra = (ahora, p)

    def _segmentos(self):
        """Partes de la linea, en el orden en que se ven."""
        partes = []
        if self.por_bytes:
            partes.append(("gb", tamano_par(self.procesado(), self.total), pasos.G))
            falta = self.total - self.procesado()
            if self.transcurrido() >= 2 and self.vel and self.vel > 0:
                eta = t("progress.left", time=tiempo_restante(falta / self.vel))
            else:
                eta = t("progress.estimating")
            partes.append(("eta", eta, pasos.A))
            if self.vel:
                partes.append(("vel", velocidad(self.vel), pasos.G))
        tarea = f"{self.i}/{self.n}"
        if self.accion:
            tarea += f" {self.accion}"
            if self.por_bytes and self.tam >= ARCHIVO_GRANDE:
                tarea += f" {int(self._parcial() * 100)}%"
        partes.append(("tarea", tarea, ""))
        if self.mostrar_nombre and self.nombre:
            partes.append(("nombre", self.nombre, pasos.G))
        return partes

    def linea(self, ancho):
        """(texto plano, texto con color) que entra en ancho columnas."""
        pct = int(self.fraccion() * 100)
        pct_txt = f"{pct:>3}%"
        util = max(20, ancho - 1 - len(self.sangria))
        # Barra de ancho fijo: si cambiara con cada dibujo, la linea "bailaria".
        barra = ancho_barra(util)
        todas = self._segmentos()
        nombre = next((p for p in todas if p[0] == "nombre"), None)
        largo_nombre = ancho_texto(nombre[1]) if nombre else 0
        # Lo esencial es el %, el tiempo que falta y que se hace con que archivo.
        # Si no cabe se sacrifica, en orden: velocidad, GB, nombre, tarea, tiempo.
        intentos = [((), 28), (("vel",), 28), (("vel", "gb"), 20), (("vel", "gb"), 12),
                    (("vel", "gb", "nombre"), 0), (("vel", "gb", "nombre", "tarea"), 0),
                    (("vel", "gb", "nombre", "tarea", "eta"), 0)]
        partes = []
        for quitar, nombre_min in intentos:
            partes = [p for p in todas if p[0] not in quitar]
            largo = barra + 2 + len(pct_txt) + sum(len(SEP) + ancho_texto(p[1])
                                                   for p in partes if p[0] != "nombre")
            if nombre and "nombre" not in quitar:
                resto = util - largo - len(SEP)
                if resto >= min(largo_nombre, nombre_min):
                    partes = [p if p[0] != "nombre" else ("nombre", recortar_medio(p[1], resto), p[2])
                              for p in partes]
                    break
            elif largo <= util:
                break
        llenos = int(round(self.fraccion() * barra))
        if self.fraccion() < 1 and llenos == barra:
            llenos = barra - 1
        plano_barra = LLENO * llenos + VACIO * (barra - llenos)
        cuerpo_plano = SEP.join(p[1] for p in partes)
        plano = f"{self.sangria}{plano_barra}  {pct_txt}" + (SEP + cuerpo_plano if partes else "")
        color_barra = self._c(LLENO * llenos, pasos.A) + self._c(VACIO * (barra - llenos), pasos.G)
        sep = self._c(SEP, pasos.G)
        cuerpo = sep.join(self._c(p[1], p[2]) if p[2] else p[1] for p in partes)
        coloreado = f"{self.sangria}{color_barra}  {self._c(pct_txt, pasos.A)}" + (sep + cuerpo if partes else "")
        return plano, coloreado

    def _dibujar(self, forzar=False):
        if not self.vivo or self._cerrado:
            return
        ahora = time.monotonic()
        if not forzar and ahora - self._ultimo < REFRESCO:
            return
        self._ultimo = ahora
        self._medir(ahora)
        ancho = shutil.get_terminal_size((100, 24)).columns
        plano, coloreado = self.linea(ancho)
        extra = ""
        pct = int(self.fraccion() * 100)
        if pct != self._pct_titulo:
            self._pct_titulo = pct
            if self.titulo:
                _titulo_consola(f"{pct}% · {self.titulo}")
            extra = self._pestana(1, pct)
        self._escribir_linea(plano, coloreado, ancho, extra)

    def cerrar(self, resumen=None, ok=True, sangria=None):
        """Borra la barra, devuelve titulo y pestana a su estado y resume."""
        sangria = self.sangria if sangria is None else sangria
        if self._cerrado:
            return
        self._cerrado = True
        self._borrar()
        if self.vivo:
            if self._titulo_original is not None:
                _titulo_consola(self._titulo_original)
            self.salida.write(self._pestana(0))
            self.salida.flush()
        if resumen:
            if self.vt:
                marca, color = pasos.MARCAS["ok" if ok else "fallo"]
                print(f"{sangria}{self._c(marca, color)} {resumen}", file=self.salida)
            else:
                print(f"{sangria}{'OK' if ok else '[X]'} {resumen}", file=self.salida)
            self.salida.flush()


class Actividad(_Linea):
    """La misma linea que Progreso para trabajos sin total conocido.

    Un tramo ambar va y viene por la barra; donde Progreso pone el
    porcentaje va el tiempo transcurrido, y despues que se hace y el ultimo
    detalle (la ultima linea de pip, por ejemplo). Con hilo=True se anima
    sola mientras corre el bloque with; si no, hay que llamar a dibujar().
    """

    PERIODO = 2.4  # segundos de ida y vuelta del tramo

    def __init__(self, etiqueta, sangria="   ", salida=None, hilo=False):
        self._iniciar_linea(salida, sangria)
        self.etiqueta = etiqueta
        self.texto = ""
        self.t0 = time.monotonic()
        self._lock = threading.Lock()
        self._fin = threading.Event()
        self._hilo = None
        if self.vivo:
            self.salida.write(self._pestana(3))
            self.dibujar()
            if hilo:
                self._hilo = threading.Thread(target=self._animar, daemon=True)
                self._hilo.start()

    def _animar(self):
        while not self._fin.wait(REFRESCO):
            self.dibujar()

    def transcurrido(self):
        return time.monotonic() - self.t0

    def detalle(self, texto):
        """Texto secundario, en gris al final de la linea."""
        self.texto = " ".join(str(texto or "").split())

    def linea(self, ancho):
        seg = int(self.transcurrido())
        reloj = f"{seg // 60}:{seg % 60:02d}".rjust(4)
        util = max(20, ancho - 1 - len(self.sangria))
        barra = ancho_barra(util)
        tramo = max(3, barra // 4)
        fase = (self.transcurrido() % self.PERIODO) / self.PERIODO
        ida = fase * 2 if fase < 0.5 else 2 - fase * 2
        pos = int(round(ida * (barra - tramo)))
        cabeza = barra + 2 + len(reloj)
        etiqueta = recortar_medio(self.etiqueta, max(8, util - cabeza - len(SEP)))
        partes = [(etiqueta, "")]
        resto = util - cabeza - len(SEP) - ancho_texto(etiqueta) - len(SEP)
        if self.texto and resto >= 12:
            partes.append((recortar_medio(self.texto, resto), pasos.G))
        antes, luz, despues = VACIO * pos, LLENO * tramo, VACIO * (barra - pos - tramo)
        plano = f"{self.sangria}{antes}{luz}{despues}  {reloj}" + "".join(SEP + p for p, _ in partes)
        sep = self._c(SEP, pasos.G)
        coloreado = (f"{self.sangria}{self._c(antes, pasos.G)}{self._c(luz, pasos.A)}"
                     f"{self._c(despues, pasos.G)}  {self._c(reloj, pasos.A)}"
                     + "".join(sep + (self._c(p, c) if c else p) for p, c in partes))
        return plano, coloreado

    def dibujar(self):
        if not self.vivo:
            return
        with self._lock:
            if self._cerrado:
                return
            ancho = shutil.get_terminal_size((100, 24)).columns
            plano, coloreado = self.linea(ancho)
            self._escribir_linea(plano, coloreado, ancho)

    def cerrar(self):
        self._fin.set()
        if self._hilo:
            self._hilo.join(timeout=2)
        with self._lock:
            if self._cerrado:
                return
            self._cerrado = True
            self._borrar()
            if self.vivo:
                self.salida.write(self._pestana(0))
                self.salida.flush()
