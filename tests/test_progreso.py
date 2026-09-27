import contextlib
import functools
import hashlib
import http.server
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import migrar_modelos as migrar
import progreso


class Consola(io.StringIO):
    """Salida que se hace pasar por una consola real."""
    def isatty(self): return True


def consola_falsa(test,columnas=110,wt=True):
    test.enterContext(patch.dict(os.environ,{"COLUMNS":str(columnas),"CINECONIA_LANG":"es"}))
    test.enterContext(patch.object(progreso,"_activar_vt",return_value=True))
    test.enterContext(patch.object(progreso,"_titulo_consola",return_value=None))
    test.enterContext(patch.object(progreso,"_WT",wt))
    test.enterContext(patch.object(progreso,"REFRESCO",0))


class LineaTests(unittest.TestCase):
    def setUp(self):
        consola_falsa(self)

    def barra(self,ancho,nombre):
        p=progreso.Progreso(50*1024**3,73,salida=Consola())
        p.archivo(34,nombre,20*1024**3,40*1024**3,"verificando")
        p.avanzar(9*1024**3)
        p.vel=180*1024**2
        p.t0-=30
        return p.linea(ancho)[0]

    def test_line_always_fits_the_window(self):
        nombres=["a.safetensors","minimax_h3_ref2va_fp8_scaled_con_un_nombre_muy_largo.safetensors",
                 "中文模型名字"*6+".safetensors"]
        for ancho in (40,60,80,100,120,160,220):
            for nombre in nombres:
                linea=self.barra(ancho,nombre)
                self.assertLessEqual(progreso.ancho_texto(linea),ancho-1,(ancho,linea))

    def test_wide_window_shows_percent_time_and_file(self):
        linea=self.barra(160,"minimax_h3_video_vae_fp16.safetensors")
        for parte in ("%","faltan ~","34/73 verificando","minimax_h3_video_vae_fp16.safetensors","GB","MB/s"):
            self.assertIn(parte,linea)

    def test_bar_width_does_not_change_between_frames(self):
        largos={self.barra(120,n).count(progreso.LLENO)+self.barra(120,n).count(progreso.VACIO)
                for n in ("a","b"*40,"c"*90)}
        self.assertEqual(len(largos),1)

    def test_long_names_keep_their_ending(self):
        corto=progreso.recortar_medio("minimax_h3_ref2va_fp8_scaled.safetensors",24)
        self.assertTrue(corto.endswith("safetensors"))
        self.assertLessEqual(progreso.ancho_texto(corto),24)

    def test_remaining_time_format(self):
        self.assertEqual(progreso.tiempo_restante(3),"5 s")
        self.assertEqual(progreso.tiempo_restante(151),"2 min 30 s")
        self.assertEqual(progreso.tiempo_restante(1500),"25 min")
        self.assertEqual(progreso.tiempo_restante(3900),"1 h 05 min")


class SalidaTests(unittest.TestCase):
    def test_redirected_output_gets_only_the_summary(self):
        salida=io.StringIO()
        with progreso.Progreso(100,1,salida=salida) as p:
            p.archivo(1,"x",100,100,"copiando")
            p.avanzar(100)
            p.terminar_archivo()
            p.cerrar("listo")
        self.assertNotIn("\r",salida.getvalue())
        self.assertIn("listo",salida.getvalue())

    def test_console_draws_and_restores_terminal_tab(self):
        consola_falsa(self)
        salida=Consola()
        with progreso.Progreso(100,1,titulo="Copiando",salida=salida) as p:
            p.archivo(1,"x",100,100,"copiando")
            p.avanzar(50)
            self.assertIn("\x1b]9;4;1;50\x07",salida.getvalue())
            p.terminar_archivo()
        self.assertTrue(salida.getvalue().endswith("\x1b]9;4;0;0\x07"))

    def test_interrupted_phase_still_restores_the_tab(self):
        consola_falsa(self)
        salida=Consola()
        with self.assertRaises(KeyboardInterrupt):
            with progreso.Progreso(100,1,salida=salida) as p:
                p.archivo(1,"x",100,100,"copiando")
                raise KeyboardInterrupt
        self.assertIn("\x1b]9;4;0;0\x07",salida.getvalue())

    def test_disabled_by_environment(self):
        with patch.dict(os.environ,{"CINECONIA_PROGRESO":"0"}):
            self.assertFalse(progreso.Progreso(1,1,salida=Consola()).vivo)


class MigracionConProgresoTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.enterContext(patch.dict(os.environ,{"LOCALAPPDATA":str(self.root/"profile")}))
        consola_falsa(self)
        self.salida=Consola()
        self.enterContext(contextlib.redirect_stdout(self.salida))
        self.src=self.root/"old/models/checkpoints"
        self.src.mkdir(parents=True)
        (self.src/"grande.safetensors").write_bytes(os.urandom(3*migrar.BLOQUE+123))
        (self.src/"chico.safetensors").write_bytes(b"BBB")

    def test_copy_reports_every_byte_and_keeps_metadata(self):
        vistos=[]
        origen=self.src/"grande.safetensors"
        os.utime(origen,(1_700_000_000,1_700_000_000))
        destino=self.root/"copia.bin"
        migrar.copiar_con_avance(str(origen),str(destino),vistos.append)
        self.assertEqual(sum(vistos),origen.stat().st_size)
        self.assertEqual(destino.read_bytes(),origen.read_bytes())
        self.assertEqual(int(destino.stat().st_mtime),1_700_000_000)

    def test_safe_move_shows_each_phase_and_reaches_100(self):
        plan,cache=migrar.construir_plan([str(self.src.parent)],str(self.root/"central/models"))
        resultado=migrar.ejecutar_plan(plan,"mover",cache)
        texto=self.salida.getvalue()
        self.assertFalse(resultado["errores"])
        self.assertEqual(resultado["eliminados_origen"],2)
        for clave in ("progress.copying","progress.verifying","progress.checking"):
            self.assertIn(migrar.t(clave),texto)
        self.assertIn("\x1b]9;4;1;100\x07",texto)
        self.assertIn("Copia lista: 2 de 2 archivos",texto)
        self.assertIn("Biblioteca verificada: 2 de 2 archivos",texto)
        self.assertIn("Originales retirados: 2 de 2",texto)

    def test_verification_failure_is_marked_and_keeps_originals(self):
        plan,cache=migrar.construir_plan([str(self.src.parent)],str(self.root/"central/models"))
        real=migrar.sha256
        def falla_en_fase_2(ruta,cache,avance=None):
            if ruta.endswith("chico.safetensors") and "central" in ruta and not cache and avance and fase2[0]:
                raise OSError("disco desconectado")
            return real(ruta,cache,avance)
        fase2=[False]
        imprimir=print
        def marcar(*a,**k):
            if a and migrar.t("migrator.verify_phase") in str(a[0]): fase2[0]=True
            imprimir(*a,**k)
        with patch.object(migrar,"sha256",side_effect=falla_en_fase_2),patch("builtins.print",side_effect=marcar):
            resultado=migrar.ejecutar_plan(plan,"mover",cache)
        self.assertTrue(resultado["errores"])
        self.assertEqual(resultado["eliminados_origen"],0)
        self.assertTrue((self.src/"chico.safetensors").exists())
        self.assertIn("Biblioteca verificada: 1 de 2 archivos",self.salida.getvalue())


class ActividadTests(unittest.TestCase):
    def test_activity_line_fits_and_shows_elapsed_time(self):
        consola_falsa(self)
        with progreso.Actividad("pip install sageattention",salida=Consola()) as a:
            a.detalle("Collecting triton-windows<3.5 (from sageattention)")
            a.t0-=75
            for ancho in (40,80,120,200):
                linea=a.linea(ancho)[0]
                self.assertLessEqual(progreso.ancho_texto(linea),ancho-1,(ancho,linea))
            self.assertIn("1:15",a.linea(120)[0])
            self.assertIn("pip install sageattention",a.linea(120)[0])

    def test_activity_thread_draws_and_marks_tab_as_busy(self):
        consola_falsa(self)
        salida=Consola()
        with progreso.Actividad("probando",salida=salida,hilo=True):
            pass
        texto=salida.getvalue()
        self.assertIn("\x1b]9;4;3;0\x07",texto)
        self.assertTrue(texto.endswith("\x1b]9;4;0;0\x07"))

    def test_activity_is_silent_when_redirected(self):
        salida=io.StringIO()
        with progreso.Actividad("pip",salida=salida,hilo=True) as a:
            a.dibujar()
        self.assertEqual(salida.getvalue(),"")


PS1=Path(__file__).resolve().parents[1]/"src/progreso.ps1"
POWERSHELL=shutil.which("powershell.exe") or shutil.which("pwsh")


class PowerShellAsciiTests(unittest.TestCase):
    def test_script_is_ascii_for_windows_powershell_5(self):
        # PowerShell 5.1 lee un .ps1 sin BOM como ANSI: una tilde lo rompe.
        PS1.read_bytes().decode("ascii")


@unittest.skipUnless(POWERSHELL,"PowerShell no disponible")
class PowerShellTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.datos=os.urandom(12*1024*1024+7)
        (self.root/"paquete.bin").write_bytes(self.datos)

    def ps(self,*args):
        env=dict(os.environ,CINECONIA_LANG="es")
        return subprocess.run([POWERSHELL,"-NoProfile","-ExecutionPolicy","Bypass","-File",str(PS1),*args],
                              capture_output=True,text=True,encoding="utf-8",errors="replace",
                              timeout=180,cwd=self.root,env=env)

    def test_probe_mode(self):
        self.assertEqual(self.ps("-Modo","prueba").returncode,0)

    def test_hash_accepts_the_right_digest_only(self):
        bueno=hashlib.sha256(self.datos).hexdigest()
        r=self.ps("-Modo","hash","-Archivo","paquete.bin","-Esperado",bueno.upper())
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn("SHA-256 verificado",r.stdout)
        self.assertEqual(self.ps("-Modo","hash","-Archivo","paquete.bin","-Esperado","0"*64).returncode,1)

    def test_download_writes_the_file_and_reports_it(self):
        manejador=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(self.root))
        manejador.log_message=lambda *a:None
        servidor=http.server.ThreadingHTTPServer(("127.0.0.1",0),manejador)
        threading.Thread(target=servidor.serve_forever,daemon=True).start()
        self.addCleanup(servidor.shutdown)
        url=f"http://127.0.0.1:{servidor.server_address[1]}/paquete.bin"
        r=self.ps("-Modo","descargar","-Url",url,"-Salida","bajado.part","-Nombre","paquete.7z")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual((self.root/"bajado.part").read_bytes(),self.datos)
        self.assertIn("Descarga lista: paquete.7z",r.stdout)

    def test_failed_download_returns_curl_error(self):
        r=self.ps("-Modo","descargar","-Url","http://127.0.0.1:1/nada.7z","-Salida","nada.part")
        self.assertNotEqual(r.returncode,0)

    @unittest.skipUnless(shutil.which("7z") or os.path.isfile(r"C:\Program Files\7-Zip\7z.exe"),"7-Zip no disponible")
    def test_extract_and_test_read_7zip_progress(self):
        siete=shutil.which("7z") or r"C:\Program Files\7-Zip\7z.exe"
        subprocess.run([siete,"a","-mx=1","p.7z","paquete.bin"],cwd=self.root,capture_output=True,check=True)
        r=self.ps("-Modo","extraer","-SieteZip",siete,"-Archivo","p.7z","-Destino","salida")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual((self.root/"salida/paquete.bin").read_bytes(),self.datos)
        self.assertIn("Extracción lista: 1 archivos",r.stdout)
        self.assertEqual(self.ps("-Modo","probar","-SieteZip",siete,"-Archivo","p.7z").returncode,0)


if __name__=="__main__": unittest.main()
