import contextlib
import io
import json
import os
from pathlib import Path
import string
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import ajustes_interfaz
import deteccion
import entorno_torch
import instalador as ins
import modelos_enlace as enlaces
import migrar_modelos as migrar
import verificacion


class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.enterContext(patch.dict(os.environ,{"LOCALAPPDATA":str(self.root/"profile"),"CINECONIA_LANG":"es"}))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))


class InstallerTests(Isolated):
    def setUp(self):
        super().setUp()
        ins.ESTADOS_NODOS.clear()
        ins.RESTRICCIONES_TORCH=None

    def node(self,valid=True):
        node=self.root/"ComfyUI/custom_nodes/ComfyUI-Cine-con-IA"
        node.mkdir(parents=True)
        if valid: (node/"__init__.py").write_text("NODE_CLASS_MAPPINGS = {}")
        (node/"requirements.txt").write_text("missing-package\n")
        return node

    def test_empty_folder_is_not_installed(self):
        self.node(False)
        self.assertFalse(ins.nodo_instalado(str(self.root),"cineconia"))

    def test_rerun_rechecks_existing_dependencies(self):
        self.node()
        with patch.object(ins,"clonar_nodo",return_value=False) as repair:
            self.assertFalse(ins.instalar_nodo(str(self.root),"python","cineconia"))
        repair.assert_called_once()

    def test_dependency_failure_is_not_success(self):
        self.node()
        with patch.object(ins,"instalar_requisitos",return_value=["missing-package"]),patch.object(ins,"proteger_torch",return_value=True):
            self.assertFalse(ins.clonar_nodo(str(self.root),"python","cineconia"))
        self.assertEqual(ins.ESTADOS_NODOS["cineconia"],"fallo")

    def test_failed_clone_preserves_previous_folder(self):
        node=self.node(False)
        (node/"user-file.txt").write_text("keep me")
        with patch.object(ins.preflight,"git_exe",return_value="git"),patch.object(ins.pasos,"correr",return_value=(False,["network failure"])):
            self.assertFalse(ins.clonar_nodo(str(self.root),"python","cineconia"))
        self.assertEqual((node/"user-file.txt").read_text(),"keep me")

    def test_successful_clone_backs_up_incomplete_folder(self):
        node=self.node(False)
        (node/"user-file.txt").write_text("keep me")
        def clone(cmd,*args,**kwargs):
            Path(cmd[-1],"__init__.py").write_text("NODE_CLASS_MAPPINGS = {}")
            return True,[]
        with patch.object(ins.preflight,"git_exe",return_value="git"),patch.object(ins.pasos,"correr",side_effect=clone),patch.object(ins,"proteger_torch",return_value=True):
            self.assertTrue(ins.clonar_nodo(str(self.root),"python","cineconia"))
        backups=list((self.root/"_cineconia/descargas-nodos").glob("*-anterior/user-file.txt"))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_text(),"keep me")

    def test_failed_torch_restore_aborts(self):
        with patch.object(ins.entorno_torch,"vigilar",return_value=(True,False)):
            with self.assertRaises(entorno_torch.EntornoNoRecuperado): ins.proteger_torch("python",{"torch":"2.13.0+cu130"})

    def test_nested_requirements_failure_remains_visible(self):
        req=self.root/"requirements.txt"
        req.write_text("-r more.txt\n")
        with patch.object(ins,"pip_instalar",return_value=False):
            self.assertTrue(ins.instalar_requisitos("python",str(req),"test"))

    def test_requirement_url_fragment_preserved(self):
        req=self.root/"requirements.txt"
        line="git+https://example.invalid/repo.git#subdirectory=lib"
        req.write_text(line+" # comment\n")
        with patch.object(ins,"pip_instalar",side_effect=[False,True]) as pip:
            self.assertEqual(ins.instalar_requisitos("python",str(req),"test"),[])
        self.assertEqual(pip.call_args.args[1],[line])

    def test_failed_pip_check_is_not_clean(self):
        with patch.object(ins.subprocess,"run",side_effect=OSError("unavailable")):
            self.assertTrue(ins.conflictos_pip("python"))

    def test_pip_check_stderr_failure_visible(self):
        with patch.object(ins.subprocess,"run",return_value=subprocess.CompletedProcess([],1,"","pip broken")):
            self.assertIn("pip broken",ins.conflictos_pip("python")[0])

    def test_constraints_reach_pip(self):
        ins.RESTRICCIONES_TORCH="protected.txt"
        self.addCleanup(setattr,ins,"RESTRICCIONES_TORCH",None)
        with patch.object(ins.pasos,"correr",return_value=(True,[])) as run:
            ins.pip_instalar("python",["package"],"package")
        self.assertIn("--constraint",run.call_args.args[0])
        self.assertIn("protected.txt",run.call_args.args[0])

    def test_amd_constraints_keep_backend(self):
        path=entorno_torch.restricciones(str(self.root),{"torch":"2.13.0+rocm7.2","torchvision":"0.28.0+rocm7.2"})
        self.assertIn("torch==2.13.0+rocm7.2",Path(path).read_text())

    def test_failed_version_switch_verifies_rollback(self):
        original={"torch":"2.13.0+cu130"}
        with patch.object(entorno_torch,"versiones",return_value=original),patch.object(entorno_torch,"arranca",side_effect=[(False,"incompatible"),(True,"2.13.0+cu130")]):
            ok,detail=entorno_torch.cambiar_rama("python",(2,11),original["torch"],lambda *args:True)
        self.assertFalse(ok)
        self.assertEqual(detail,"incompatible")

    def test_failed_version_switch_cannot_claim_failed_rollback_succeeded(self):
        original={"torch":"2.13.0+cu130"}
        with patch.object(entorno_torch,"versiones",side_effect=[original,{"torch":"2.11.0+cu130"}]),patch.object(entorno_torch,"arranca",return_value=(False,"incompatible")):
            with self.assertRaises(entorno_torch.EntornoNoRecuperado):
                entorno_torch.cambiar_rama("python",(2,11),original["torch"],lambda *args:True)

    def test_intel_unavailable_is_reported(self):
        torch={"torch":"2.13.0+xpu","cuda":None,"hip":None,"xpu_available":False,"cuda_available":False}
        with patch.object(deteccion,"entorno_torch",return_value=torch),patch.object(deteccion,"driver_nvidia",return_value=None),patch.object(deteccion,"adaptadores_windows",return_value=[{"Name":"Intel Arc"}]):
            self.assertTrue(deteccion.informe("python",str(self.root),"intel")["gpu_inutilizable"])

    def test_group_dependency_failure_is_not_green(self):
        class Steps:
            def cerrar(self,*args): self.result=args
        ins.ESTADOS_NODOS["rgthree"]="fallo"
        steps=Steps()
        with patch.object(ins,"instalar_grupo",return_value=(["customscripts"],True)):
            ins.paso_grupo(steps,str(self.root),"python","interfaz")
        self.assertEqual(steps.result[0],"fallo")


class StartupTests(unittest.TestCase):
    def test_success_summary(self):
        self.assertEqual(verificacion.analizar(["Import times for custom nodes:",r"   0.1 seconds: C:\ComfyUI\custom_nodes\rgthree-comfy"],["rgthree-comfy"]),([],[]))

    def test_failed_import_not_counted(self):
        missing,errors=verificacion.analizar([r"   0.1 seconds (IMPORT FAILED): C:\ComfyUI\custom_nodes\rgthree-comfy"],["rgthree-comfy"])
        self.assertEqual(missing,["rgthree-comfy"])
        self.assertTrue(errors)

    def test_silently_missing_node_is_not_success(self):
        self.assertEqual(verificacion.analizar([],["example"])[0],["example"])

    def test_partial_node_import_error_reported(self):
        self.assertTrue(verificacion.analizar(["Node `Example` import failed:"],[])[1])

    def test_prestartup_success_is_not_node_load(self):
        self.assertEqual(verificacion.analizar(["Prestartup times for custom nodes:",r"0.1 seconds: C:\ComfyUI\custom_nodes\rgthree-comfy"],["rgthree-comfy"])[0],["rgthree-comfy"])


class StartupProcessTests(Isolated):
    def check_start(self,output,code=0):
        root=self.root/"ComfyUI"
        (root/"comfy").mkdir(parents=True)
        (root/"comfy/cli_args.py").write_text("--quick-test-for-ci --disable-auto-launch --disable-all-custom-nodes --whitelist-custom-nodes")
        (root/"main.py").write_text(f"import sys\nprint('Import times for custom nodes:')\nprint({output!r})\nsys.exit({code})\n")
        return verificacion.comprobar(str(self.root),sys.executable,["test-node"])

    def test_real_subprocess_success(self):
        ok,detail=self.check_start("0.1 seconds: C:/ComfyUI/custom_nodes/test-node")
        self.assertTrue(ok,detail)

    def test_zero_exit_with_import_failure_is_failure(self):
        ok,detail=self.check_start("0.1 seconds (IMPORT FAILED): C:/ComfyUI/custom_nodes/test-node")
        self.assertFalse(ok)

    def test_nonzero_exit_is_failure_even_after_import(self):
        ok,detail=self.check_start("0.1 seconds: C:/ComfyUI/custom_nodes/test-node",1)
        self.assertFalse(ok)

    def test_timeout_stops_child(self):
        ok,lines=ins.pasos.correr([sys.executable,"-c","import time; time.sleep(30)"],"test",timeout=.1,completo=True)
        self.assertFalse(ok)
        self.assertTrue(any("TIMEOUT" in line for line in lines))


class MigrationTests(Isolated):
    def files(self):
        src=self.root/"old/models/checkpoints"
        dst=self.root/"central/models"
        src.mkdir(parents=True)
        (src/"a.safetensors").write_bytes(b"AAA")
        (src/"b.safetensors").write_bytes(b"BBB")
        plan,cache=migrar.construir_plan([str(src.parent)],str(dst))
        return src,dst,plan,cache

    def test_copy_preserves_originals(self):
        src,dst,plan,cache=self.files()
        result=migrar.ejecutar_plan(plan,"copiar",cache)
        self.assertFalse(result["errores"])
        self.assertTrue((src/"a.safetensors").exists())
        self.assertEqual((dst/"checkpoints/a.safetensors").read_bytes(),b"AAA")

    def test_safe_move_finishes_all_copies_before_delete(self):
        src,dst,plan,cache=self.files()
        seen=[]
        def checkpoint(result):
            seen.append(True)
            self.assertEqual(len(result["archivos"]),2)
            for item in result["archivos"]:
                self.assertTrue(Path(item["origen"]).exists())
                self.assertEqual(migrar.sha256(item["destino"],{}),item["sha256"])
        result=migrar.ejecutar_plan(plan,"mover",cache,checkpoint)
        self.assertEqual(seen,[True])
        self.assertFalse(result["errores"])
        self.assertEqual(result["eliminados_origen"],2)
        self.assertFalse((src/"a.safetensors").exists())

    def test_second_copy_failure_keeps_every_original(self):
        src,dst,plan,cache=self.files()
        copy=migrar.copiar_verificar
        def fail_second(a,b,c,*rest):
            if a.endswith("b.safetensors"): raise OSError("disk disconnected")
            return copy(a,b,c,*rest)
        with patch.object(migrar,"copiar_verificar",side_effect=fail_second):
            result=migrar.ejecutar_plan(plan,"mover",cache)
        self.assertTrue(result["errores"])
        self.assertEqual(result["eliminados_origen"],0)
        self.assertTrue(all(Path(x["origen"]).exists() for x in plan))

    def test_report_failure_prevents_all_deletions(self):
        src,dst,plan,cache=self.files()
        def fail(result): raise OSError("cannot write report")
        result=migrar.ejecutar_plan(plan,"mover",cache,fail)
        self.assertEqual(result["eliminados_origen"],0)
        self.assertTrue(result["errores"])
        self.assertTrue(all(Path(x["origen"]).exists() for x in plan))

    def test_changed_destination_is_not_deleted_from_source(self):
        src,dst,plan,cache=self.files()
        def tamper(result): Path(result["archivos"][0]["destino"]).write_bytes(b"changed")
        result=migrar.ejecutar_plan(plan,"mover",cache,tamper)
        self.assertEqual(result["eliminados_origen"],0)
        self.assertTrue(result["errores"])
        self.assertTrue(all(Path(x["origen"]).exists() for x in plan))

    def test_conflicts_preserve_both_contents(self):
        src,dst,_,_=self.files()
        (dst/"checkpoints").mkdir(parents=True)
        (dst/"checkpoints/a.safetensors").write_bytes(b"different")
        plan,cache=migrar.construir_plan([str(src.parent)],str(dst))
        result=migrar.ejecutar_plan(plan,"copiar",cache)
        self.assertEqual(result["conflictos"],1)
        self.assertEqual((dst/"checkpoints/a.safetensors").read_bytes(),b"different")
        self.assertEqual((dst/"checkpoints/a__conflicto_2.safetensors").read_bytes(),b"AAA")

    def test_duplicate_verified_before_original_removed(self):
        src,dst,plan,cache=self.files()
        migrar.ejecutar_plan(plan,"copiar",cache)
        plan,cache=migrar.construir_plan([str(src.parent)],str(dst))
        result=migrar.ejecutar_plan(plan,"mover",cache)
        self.assertEqual(result["duplicados"],2)
        self.assertEqual(result["eliminados_origen"],2)
        self.assertEqual((dst/"checkpoints/a.safetensors").read_bytes(),b"AAA")

    def test_move_reserves_space_even_on_same_disk(self):
        src,dst,plan,cache=self.files()
        self.assertEqual(migrar.espacio_requerido(plan,str(dst),"mover"),6+migrar.MARGEN_BYTES)

    def test_same_source_and_destination_not_deleted(self):
        src,dst,plan,cache=self.files()
        plan[0]["destino"]=plan[0]["origen"]
        result=migrar.ejecutar_plan(plan,"mover",cache)
        self.assertTrue(result["errores"])
        self.assertEqual(result["eliminados_origen"],0)


class LibraryTests(Isolated):
    def test_registration_survives_new_install_location(self):
        library=self.root/"deep"/"one"/"two"/"three"/"models"
        (library/"checkpoints").mkdir(parents=True)
        enlaces.registrar_biblioteca(str(library))
        with patch.object(enlaces,"discos_fijos",return_value=[]),patch.object(enlaces.os.path,"expanduser",return_value=str(self.root/"absent")):
            self.assertEqual(enlaces.detectar_instalaciones(profundidad=0),[str(library.resolve())])

    def test_unplugged_library_is_remembered_but_not_listed_as_available(self):
        library=self.root/"offline/models"
        enlaces.registrar_biblioteca(str(library))
        with patch.object(enlaces,"discos_fijos",return_value=[]),patch.object(enlaces.os.path,"expanduser",return_value=str(self.root/"absent")):
            self.assertEqual(enlaces.detectar_instalaciones(profundidad=0),[])
        self.assertEqual(enlaces.bibliotecas_guardadas(),[str(library.resolve())])

    def test_shared_config_preserves_unrelated_settings(self):
        library=self.root/"central/models"
        library.mkdir(parents=True)
        enlaces.registrar_biblioteca(str(library))
        for name in ("ComfyUI-one","ComfyUI-two"):
            root=self.root/name
            root.mkdir()
            config=root/"extra_model_paths.yaml"
            config.write_text('other:\n    base_path: "D:/existing"\n')
            path,backup=enlaces.actualizar_yaml(str(root),str(library))
            text=Path(path).read_text()
            self.assertIn('other:\n    base_path: "D:/existing"',text)
            self.assertIn("is_default: true",text)
            self.assertIn(library.as_posix(),text)
            self.assertEqual(Path(backup).read_text(),'other:\n    base_path: "D:/existing"\n')
            enlaces.actualizar_yaml(str(root),str(library))
            self.assertEqual(config.read_text().count(enlaces.MARCA_INICIO),1)
        self.assertFalse((self.root/"ComfyUI-one/models").exists())

    def test_corrupt_registry_does_not_crash(self):
        path=Path(enlaces.ruta_registro())
        path.parent.mkdir(parents=True)
        path.write_text("not json")
        self.assertEqual(enlaces.bibliotecas_guardadas(),[])

    def test_invalid_registry_schema_does_not_crash(self):
        path=Path(enlaces.ruta_registro())
        path.parent.mkdir(parents=True)
        path.write_text('{"bibliotecas": null}')
        self.assertEqual(enlaces.bibliotecas_guardadas(),[])


class UiSettingsTests(Isolated):
    def settings(self):
        return self.root/"ComfyUI/user/default/comfy.settings.json"

    def write_settings(self,text):
        path=self.settings()
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding="utf-8")
        return path

    def test_new_install_gets_docked_queue(self):
        state,backup=ajustes_interfaz.aplicar(str(self.root))
        self.assertEqual(state,"ok")
        self.assertIsNone(backup)
        data=json.loads(self.settings().read_text(encoding="utf-8"))
        self.assertIs(data["Comfy.Queue.QPOV2"],True)
        self.assertIs(data["Comfy.Queue.ShowRunProgressBar"],False)

    def test_existing_settings_are_preserved_and_backed_up(self):
        original='{"Comfy.Locale": "es", "Comfy.ColorPalette": "dark"}'
        path=self.write_settings(original)
        state,backup=ajustes_interfaz.aplicar(str(self.root))
        self.assertEqual(state,"ok")
        data=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual((data["Comfy.Locale"],data["Comfy.ColorPalette"]),("es","dark"))
        self.assertIs(data["Comfy.Queue.QPOV2"],True)
        self.assertEqual(Path(backup).read_text(encoding="utf-8"),original)

    def test_user_choice_is_not_overwritten(self):
        path=self.write_settings('{"Comfy.Queue.QPOV2": false}')
        ajustes_interfaz.aplicar(str(self.root))
        data=json.loads(path.read_text(encoding="utf-8"))
        self.assertIs(data["Comfy.Queue.QPOV2"],False)
        self.assertIs(data["Comfy.Queue.ShowRunProgressBar"],False)

    def test_settings_with_bom_are_read(self):
        path=self.write_settings('\ufeff{"Comfy.Locale": "es"}')
        self.assertEqual(ajustes_interfaz.aplicar(str(self.root))[0],"ok")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["Comfy.Locale"],"es")

    def test_rerun_changes_nothing(self):
        ajustes_interfaz.aplicar(str(self.root))
        before=self.settings().read_bytes()
        self.assertEqual(ajustes_interfaz.aplicar(str(self.root)),("igual",None))
        self.assertEqual(self.settings().read_bytes(),before)
        self.assertEqual(len(list(self.settings().parent.iterdir())),1)

    def test_unreadable_settings_are_left_untouched(self):
        for text in ("not json","[1, 2]"):
            path=self.write_settings(text)
            self.assertEqual(ajustes_interfaz.aplicar(str(self.root))[0],"error")
            self.assertEqual(path.read_text(encoding="utf-8"),text)
        self.assertEqual(len(list(self.settings().parent.iterdir())),1)

    def test_installer_reports_failure_without_stopping(self):
        with patch.object(ins.ajustes_interfaz,"aplicar",return_value=("error","disco lleno")):
            self.assertEqual(ins.ajustar_interfaz(str(self.root)),"error")


class PackagingTests(unittest.TestCase):
    def test_bat_files_are_crlf(self):
        for path in Path(__file__).resolve().parents[1].glob("*.bat"):
            self.assertNotIn(b"\n",path.read_bytes().replace(b"\r\n",b""),path.name)

    def test_both_languages_have_same_keys_and_placeholders(self):
        root=Path(__file__).resolve().parents[1]/"src/locales"
        es=json.loads((root/"es.json").read_text(encoding="utf-8"))
        en=json.loads((root/"en.json").read_text(encoding="utf-8"))
        self.assertEqual(set(es),set(en))
        fields=lambda text:{f for _,f,_,_ in string.Formatter().parse(text) if f}
        for key in es: self.assertEqual(fields(es[key]),fields(en[key]),key)


if __name__=="__main__": unittest.main()
